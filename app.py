from flask import Flask, jsonify, request
from flask_cors import CORS
from playwright.sync_api import sync_playwright
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

def estrai_partite_palermo():
    """Estrae le partite dal sito del Palermo"""
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
            
    except Exception as e:
        print(f"Errore generale: {e}")
        return []

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
        "message": "API Calendario Palermo FC attiva",
        "endpoints": {
            "/api/partite": "Tutte le partite",
            "/api/partite/casa": "Solo partite in casa",
            "/health": "Health check"
        }
    })

@app.route('/api/partite', methods=['GET'])
def get_partite():
    try:
        partite = estrai_partite_palermo()
        
        solo_casa = request.args.get('casa', 'false').lower() == 'true'
        if solo_casa:
            partite = [p for p in partite if p.get('homeTeam') == 'Palermo']
        
        return jsonify({
            "success": True,
            "count": len(partite),
            "data": partite
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/partite/casa', methods=['GET'])
def get_partite_casa():
    try:
        partite = estrai_partite_palermo()
        partite_casa = [p for p in partite if p.get('homeTeam') == 'Palermo']
        
        return jsonify({
            "success": True,
            "count": len(partite_casa),
            "data": partite_casa
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
