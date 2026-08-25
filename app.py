from flask import Flask, jsonify, request
from flask_cors import CORS
from requests_html import HTMLSession
import re
from datetime import datetime
import logging
import os
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ==========================================================
# CONFIGURAZIONE STAGIONE - Cambiare SOLO questa variabile
# ogni nuova stagione (es. "2627" -> "2728")
# ==========================================================
SEASON = "2627"
SEASON_URL = f'https://www.palermofc.com/it/{SEASON}/stagione/'


def estrai_partite_palermo():
    """Estrae le partite dal sito del Palermo usando requests-html"""
    session = None
    try:
        logger.info("🔍 Inizio estrazione partite...")
        
        session = HTMLSession()
        url = SEASON_URL
        
        logger.info(f"📡 Recupero pagina: {url}")
        response = session.get(url, timeout=30)
        
        logger.info("⚙️ Rendering JavaScript con click su 'Tutte'...")
        
        # Script JavaScript che verrà eseguito durante il rendering
        js_script = """
        () => {
            return new Promise((resolve) => {
                let attempts = 0;
                const maxAttempts = 20; // fino a ~10 secondi di tentativi (20 x 500ms)
                
                function tryClick() {
                    attempts++;
                    const allTags = document.querySelectorAll('.tag_element');
                    
                    if (allTags.length === 0) {
                        if (attempts >= maxAttempts) {
                            resolve('timeout_no_tags_after_' + attempts + '_tries');
                            return;
                        }
                        setTimeout(tryClick, 500);
                        return;
                    }
                    
                    // Trovati dei tag: cerca quello/i con testo "Tutte"
                    const tutteTags = [];
                    allTags.forEach(tag => {
                        if (tag.textContent.trim() === 'Tutte') {
                            tutteTags.push(tag);
                        }
                    });
                    
                    if (tutteTags.length === 0) {
                        if (attempts >= maxAttempts) {
                            const allTexts = Array.from(allTags).map(t => t.textContent.trim()).join('|');
                            resolve('timeout_no_TUTTE_after_' + attempts + '_tries_found=[' + allTexts + ']');
                            return;
                        }
                        setTimeout(tryClick, 500);
                        return;
                    }
                    
                    // Trovati: clicca tutti quelli non ancora attivi
                    let clicked = 0;
                    tutteTags.forEach(tag => {
                        if (!tag.classList.contains('active')) {
                            tag.click();
                            clicked++;
                        }
                    });
                    
                    // Aspetta che il contenuto si aggiorni dopo il click
                    setTimeout(() => {
                        resolve('ok_attempts=' + attempts + '_tutteFound=' + tutteTags.length + '_clicked=' + clicked);
                    }, 3000);
                }
                
                tryClick();
            });
        }
        """
        
        # Render con polling per cliccare "Tutte" appena disponibile nel DOM
        render_result = response.html.render(timeout=50, sleep=2, script=js_script)
        logger.info(f"🔍 DEBUG risultato click 'Tutte': {render_result}")
        
        logger.info("✅ Rendering completato")
        
        # Aspetta ulteriormente per assicurarsi che le partite siano caricate
        time.sleep(2)
        
        # Cerca i match cards
        match_cards = response.html.find('.match-card')
        logger.info(f"🎯 Trovati {len(match_cards)} match cards")
        
        partite = []
        
        for idx, card in enumerate(match_cards):
            try:
                comp_elem = card.find('.match-card__info--league p', first=True)
                competition = comp_elem.text.strip() if comp_elem else ""
                
                round_elem = card.find('.match-card__info--league label', first=True)
                round_text = round_elem.text.strip() if round_elem else ""
                
                # FALLBACK: se il selettore primario non trova nulla (es. dopo un
                # redesign del sito che rinomina classi/tag), cerca il pattern
                # testuale della giornata ovunque nel testo della card.
                if not round_text:
                    card_text = card.text
                    m = re.search(r'\b\d{1,2}ª\b', card_text)
                    if m:
                        round_text = m.group(0)
                    else:
                        m2 = re.search(
                            r'\b(Primo|Secondo|Terzo|Quarto|Quinto)\s+turno\b'
                            r'|\bOttavi\b|\bQuarti\b|\bSemifinale\b|\bFinale\b',
                            card_text, re.IGNORECASE
                        )
                        if m2:
                            round_text = m2.group(0)
                        elif competition and competition.lower() not in ("serie bkt", "serie b"):
                            # amichevoli/tornei non di campionato senza pattern riconoscibile
                            round_text = competition
                
                date_elem = card.find('.match-card__info--match-time h3', first=True)
                date_text = date_elem.text.strip() if date_elem else ""
                
                time_elem = card.find('.match-card__info--match-time p', first=True)
                time_text = time_elem.text.strip() if time_elem else ""
                
                team_imgs = card.find('.match-card__teams--team picture img')
                teams = []
                for img in team_imgs:
                    alt = img.attrs.get('alt', '')
                    if alt:
                        teams.append(alt.strip())
                
                score_spans = card.find('.match-card__teams--score span')
                scores = []
                for span in score_spans:
                    text = span.text.strip()
                    if text and text.isdigit():
                        scores.append(int(text))
                
                match_center_link = None
                link_elem = card.find('.match-card__buttons a', first=True)
                if link_elem:
                    match_center_link = link_elem.attrs.get('href')
                
                iso_date = converti_data_italiana(date_text)
                status = "finished" if len(scores) == 2 else "scheduled"
                
                partita = {
                    "id": idx + 1,
                    "competition": competition,
                    "round": round_text,
                    "date": iso_date,
                    "time": time_text,
                    "homeTeam": teams[0] if len(teams) > 0 else "",
                    "awayTeam": teams[1] if len(teams) > 1 else "",
                    "status": status
                }
                
                if len(scores) == 2:
                    partita["homeScore"] = scores[0]
                    partita["awayScore"] = scores[1]
                
                if match_center_link:
                    partita["matchCenter"] = match_center_link
                
                partite.append(partita)
                
            except Exception as e:
                logger.error(f"❌ Errore partita {idx}: {e}")
                continue
        
        logger.info(f"🎉 Estrazione completata: {len(partite)} partite totali")
        
        # ===== DEBUG TEMPORANEO =====
        logger.info("🔍 DEBUG: elenco completo di tutte le partite estratte:")
        for p in partite:
            logger.info(
                f"🔍   id={p.get('id')} home='{p.get('homeTeam')}' away='{p.get('awayTeam')}' "
                f"round='{p.get('round')}' comp='{p.get('competition')}' status='{p.get('status')}' date='{p.get('date')}'"
            )
        # ===== FINE DEBUG TEMPORANEO =====
        
        return partite
        
    except Exception as e:
        logger.error(f"❌ Errore generale: {e}")
        return []
    finally:
        if session:
            try:
                session.close()
            except:
                pass

def converti_data_italiana(data_text):
    """Converte data italiana in formato ISO"""
    mesi = {
        'gennaio': '01', 'febbraio': '02', 'marzo': '03', 'aprile': '04',
        'maggio': '05', 'giugno': '06', 'luglio': '07', 'agosto': '08',
        'settembre': '09', 'ottobre': '10', 'novembre': '11', 'dicembre': '12'
    }
    
    try:
        match = re.search(r'(\d+)\s+(\w+)\s+(\d{4})', data_text)
        if match:
            giorno = match.group(1).zfill(2)
            mese_nome = match.group(2).lower()
            anno = match.group(3)
            mese = mesi.get(mese_nome, '01')
            return f"{anno}-{mese}-{giorno}"
    except:
        pass
    
    return ""

@app.route('/')
def home():
    return jsonify({
        "status": "ok",
        "service": "API Calendario Palermo FC",
        "version": "3.1",
        "endpoints": {
            "/api/partite": "Tutte le partite",
            "/api/partite/casa": "Solo partite in casa del Palermo",
            "/api/partite/trasferta": "Solo partite in trasferta del Palermo",
            "/health": "Health check"
        },
        "note": "Questa API estrae automaticamente TUTTE le partite cliccando sul pulsante 'Tutte'"
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/partite', methods=['GET'])
def get_partite():
    try:
        logger.info("📥 Richiesta ricevuta: /api/partite")
        partite = estrai_partite_palermo()
        
        if not partite:
            logger.warning("⚠️ Nessuna partita estratta")
            return jsonify({
                "success": False,
                "error": "Impossibile estrarre partite dal sito",
                "count": 0,
                "data": []
            }), 500
        
        solo_casa = request.args.get('casa', 'false').lower() == 'true'
        if solo_casa:
            partite = [p for p in partite if p.get('homeTeam') == 'Palermo']
            logger.info(f"🏠 Filtrate solo partite in casa: {len(partite)}")
        
        return jsonify({
            "success": True,
            "count": len(partite),
            "data": partite,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Errore nell'endpoint: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/partite/casa', methods=['GET'])
def get_partite_casa():
    try:
        logger.info("📥 Richiesta ricevuta: /api/partite/casa")
        partite = estrai_partite_palermo()
        
        if not partite:
            logger.warning("⚠️ Nessuna partita estratta")
            return jsonify({
                "success": False,
                "error": "Impossibile estrarre partite dal sito",
                "count": 0,
                "data": []
            }), 500
        
        partite_casa = [p for p in partite if p.get('homeTeam') == 'Palermo']
        logger.info(f"🏠 Partite in casa: {len(partite_casa)}")
        
        return jsonify({
            "success": True,
            "count": len(partite_casa),
            "data": partite_casa,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Errore nell'endpoint: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/partite/trasferta', methods=['GET'])
def get_partite_trasferta():
    """Endpoint per ottenere solo le partite in TRASFERTA del Palermo"""
    try:
        logger.info("📥 Richiesta ricevuta: /api/partite/trasferta")
        partite = estrai_partite_palermo()
        
        if not partite:
            logger.warning("⚠️ Nessuna partita estratta")
            return jsonify({
                "success": False,
                "error": "Impossibile estrarre partite dal sito",
                "count": 0,
                "data": []
            }), 500
        
        # Filtra solo le partite dove Palermo è squadra in trasferta (awayTeam)
        partite_trasferta = [p for p in partite if p.get('awayTeam') == 'Palermo']
        logger.info(f"✈️ Partite in trasferta: {len(partite_trasferta)}")
        
        return jsonify({
            "success": True,
            "count": len(partite_trasferta),
            "data": partite_trasferta,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Errore nell'endpoint: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
