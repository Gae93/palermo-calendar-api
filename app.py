from flask import Flask, jsonify, request
from flask_cors import CORS
from playwright.sync_api import sync_playwright
from requests_html import HTMLSession
import re
from datetime import datetime
import logging

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def estrai_partite_palermo():
    """Estrae le partite dal sito del Palermo"""
    """Estrae le partite dal sito del Palermo usando requests-html"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto('https://www.palermofc.com/it/2526/stagione/', 
                     wait_until='networkidle', 
                     timeout=30000)
            
            page.wait_for_selector('.match-card', timeout=10000)
            
            partite = []
            match_cards = page.query_selector_all('.match-card')
            
            for idx, card in enumerate(match_cards):
                try:
                    comp_elem = card.query_selector('.match-card__info--league p')
                    competition = comp_elem.inner_text().strip() if comp_elem else ""
                    
                    round_elem = card.query_selector('.match-card__info--league label')
                    round_text = round_elem.inner_text().strip() if round_elem else ""
                    
                    date_elem = card.query_selector('.match-card__info--match-time h3')
                    date_text = date_elem.inner_text().strip() if date_elem else ""
                    
                    time_elem = card.query_selector('.match-card__info--match-time p')
                    time_text = time_elem.inner_text().strip() if time_elem else ""
                    
                    team_elems = card.query_selector_all('.match-card__teams--team picture img')
                    teams = [team.get_attribute('alt').strip() for team in team_elems if team.get_attribute('alt')]
                    
                    score_elems = card.query_selector_all('.match-card__teams--score span')
                    scores = []
                    for score in score_elems:
                        score_text = score.inner_text().strip()
                        if score_text and score_text.isdigit():
                            scores.append(int(score_text))
                    
                    match_center_link = None
                    link_elem = card.query_selector('.match-card__buttons a')
                    if link_elem:
                        match_center_link = link_elem.get_attribute('href')
                    
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
                    print(f"Errore partita {idx}: {e}")
                    continue
            
            browser.close()
            return partite
            
        logger.info("🔍 Inizio estrazione partite...")
        
        session = HTMLSession()
        url = 'https://www.palermofc.com/it/2526/stagione/'
        
        # Fetch della pagina
        logger.info(f"📡 Recupero pagina: {url}")
        response = session.get(url, timeout=30)
        
        # Renderizza JavaScript
        logger.info("⚙️ Rendering JavaScript...")
        response.html.render(timeout=30, sleep=3)
        
        # Cerca i match cards
        match_cards = response.html.find('.match-card')
        logger.info(f"🎯 Trovati {len(match_cards)} match cards")
        
        partite = []
        
        for idx, card in enumerate(match_cards):
            try:
                # Estrai competizione
                comp_elem = card.find('.match-card__info--league p', first=True)
                competition = comp_elem.text.strip() if comp_elem else ""
                
                # Estrai giornata
                round_elem = card.find('.match-card__info--league label', first=True)
                round_text = round_elem.text.strip() if round_elem else ""
                
                # Estrai data
                date_elem = card.find('.match-card__info--match-time h3', first=True)
                date_text = date_elem.text.strip() if date_elem else ""
                
                # Estrai ora
                time_elem = card.find('.match-card__info--match-time p', first=True)
                time_text = time_elem.text.strip() if time_elem else ""
                
                # Estrai squadre
                team_imgs = card.find('.match-card__teams--team picture img')
                teams = []
                for img in team_imgs:
                    alt = img.attrs.get('alt', '')
                    if alt:
                        teams.append(alt.strip())
                
                # Estrai punteggio
                score_spans = card.find('.match-card__teams--score span')
                scores = []
                for span in score_spans:
                    text = span.text.strip()
                    if text and text.isdigit():
                        scores.append(int(text))
                
                # Estrai link match center
                match_center_link = None
                link_elem = card.find('.match-card__buttons a', first=True)
                if link_elem:
                    match_center_link = link_elem.attrs.get('href')
                
                # Converti data
                iso_date = converti_data_italiana(date_text)
                
                # Determina status
                status = "finished" if len(scores) == 2 else "scheduled"
                
                # Crea oggetto partita
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
                logger.info(f"✅ Partita {idx+1}: {partita['homeTeam']} vs {partita['awayTeam']}")
                
            except Exception as e:
                logger.error(f"❌ Errore partita {idx}: {e}")
                continue
        
        session.close()
        logger.info(f"🎉 Estrazione completata: {len(partite)} partite")
        return partite
        
    except Exception as e:
        print(f"Errore generale: {e}")
        logger.error(f"❌ Errore generale: {e}")
        return []

def converti_data_italiana(data_text):
@@ -109,56 +140,106 @@ def converti_data_italiana(data_text):

@app.route('/')
def home():
    """Homepage con info API"""
    return jsonify({
        "status": "ok",
        "message": "API Calendario Palermo FC attiva",
        "service": "API Calendario Palermo FC",
        "version": "2.0",
        "endpoints": {
            "/api/partite": "Tutte le partite",
            "/api/partite/casa": "Solo partite in casa",
            "/api/partite/casa": "Solo partite in casa del Palermo",
            "/health": "Health check"
        },
        "usage": {
            "example": "/api/partite/casa",
            "response": {
                "success": True,
                "count": 19,
                "data": "[array di partite...]"
            }
        }
    })

@app.route('/health')
def health_check():
    """Health check per monitoraggio"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/partite', methods=['GET'])
def get_partite():
    """Endpoint per tutte le partite"""
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
        
        # Filtra se richiesto solo casa
        solo_casa = request.args.get('casa', 'false').lower() == 'true'
        if solo_casa:
            partite = [p for p in partite if p.get('homeTeam') == 'Palermo']
            logger.info(f"🏠 Filtrate solo partite in casa: {len(partite)}")

        return jsonify({
            "success": True,
            "count": len(partite),
            "data": partite
            "data": partite,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Errore nell'endpoint: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/partite/casa', methods=['GET'])
def get_partite_casa():
    """Endpoint per solo partite in casa"""
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
        
        # Filtra solo partite in casa
        partite_casa = [p for p in partite if p.get('homeTeam') == 'Palermo']
        logger.info(f"🏠 Partite in casa: {len(partite_casa)}")

        return jsonify({
            "success": True,
            "count": len(partite_casa),
            "data": partite_casa
            "data": partite_casa,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Errore nell'endpoint: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    port = int(os.environ.get('PORT', 5000))
