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

def estrai_partite_palermo():
    """Estrae le partite dal sito del Palermo usando requests-html"""
    session = None
    try:
        logger.info("🔍 Inizio estrazione partite...")
        
        session = HTMLSession()
        url = 'https://www.palermofc.com/it/2526/stagione/'
        
        logger.info(f"📡 Recupero pagina: {url}")
        response = session.get(url, timeout=30)
        
        logger.info("⚙️ Rendering JavaScript...")
        
        # Render con script personalizzato per cliccare "Tutte"
        response.html.render(
            timeout=30, 
            sleep=2,
            script="""
                () => {
                    // Aspetta un po' per il caricamento
                    return new Promise((resolve) => {
                        setTimeout(() => {
                            // Cerca il container dei filtri
                            const filterContainer = document.querySelector('.season-node__tabs__filters');
                            if (!filterContainer) {
                                resolve('no_container');
                                return;
                            }
                            
                            // Cerca tutti i tag_element
                            const tags = filterContainer.querySelectorAll('.tag_element');
                            
                            // Cerca il tag con testo "Tutte"
                            let tutteTag = null;
                            tags.forEach(tag => {
                                const text = tag.textContent.trim();
                                if (text === 'Tutte' || text.toLowerCase() === 'tutte') {
                                    tutteTag = tag;
                                }
                            });
                            
                            if (tutteTag) {
                                // Controlla se è già attivo
                                if (tutteTag.classList.contains('active')) {
                                    resolve('already_active');
                                    return;
                                }
                                
                                // Click sul tag
                                tutteTag.click();
                                
                                // Aspetta il caricamento
                                setTimeout(() => {
                                    resolve('clicked');
                                }, 3000);
                            } else {
                                resolve('not_found');
                            }
                        }, 1000);
                    });
                }
            """
        )
        
        logger.info("✅ Rendering completato con script 'Tutte'")
        
        # Aspetta ulteriormente per il caricamento delle partite
        time.sleep(2)
        
        # VECCHIO METODO - Non più necessario
        """
        logger.info("🔘 Cerco pulsante 'Tutte'...")
        try:
            # Usa il selettore esatto trovato nell'HTML
            click_success = None
            if hasattr(response.html, 'page') and response.html.page:
                click_success = response.html.page.evaluate("""
                () => {
                    // Cerca il container dei filtri
                    const filterContainer = document.querySelector('.season-node__tabs__filters');
                    if (!filterContainer) {
                        console.log('Container filtri non trovato');
                        return false;
                    }
                    
                    // Cerca tutti i tag_element
                    const tags = filterContainer.querySelectorAll('.tag_element');
                    console.log('Tag trovati:', tags.length);
                    
                    // Cerca il tag con testo "Tutte"
                    let tutteTag = null;
                    tags.forEach(tag => {
                        const text = tag.textContent.trim();
                        console.log('Tag text:', text);
                        if (text === 'Tutte' || text.toLowerCase() === 'tutte') {
                            tutteTag = tag;
                        }
                    });
                    
                    if (tutteTag) {
                        console.log('Trovato tag Tutte, verifico se già attivo...');
                        
                        // Controlla se è già attivo
                        if (tutteTag.classList.contains('active')) {
                            console.log('Tag già attivo!');
                            return 'already_active';
                        }
                        
                        // Click sul tag
                        console.log('Click su Tutte...');
                        tutteTag.click();
                        
                        // Aspetta un attimo per il caricamento
                        return 'clicked';
                    }
                    
                    console.log('Tag Tutte non trovato');
                }
            """
        )
        """
        
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
        "version": "3.0",
        "endpoints": {
            "/api/partite": "Tutte le partite",
            "/api/partite/casa": "Solo partite in casa del Palermo",
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
