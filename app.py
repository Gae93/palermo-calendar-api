from flask import Flask, jsonify, request
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def get_chrome_driver():
    """Configura Chrome driver per Render"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def converti_data_italiana(data_text):
    """Converte data italiana in ISO"""
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

def estrai_partite_palermo():
    """Estrae partite con Selenium"""
    driver = None
    try:
        logger.info("🔍 Avvio estrazione...")
        driver = get_chrome_driver()
        
        url = 'https://www.palermofc.com/it/2526/stagione/'
        logger.info(f"📡 Caricamento: {url}")
        driver.get(url)
        
        # Aspetta caricamento match cards
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "match-card"))
        )
        
        logger.info("⏳ Attesa rendering...")
        import time
        time.sleep(3)
        
        match_cards = driver.find_elements(By.CLASS_NAME, "match-card")
        logger.info(f"🎯 Trovati {len(match_cards)} match cards")
        
        partite = []
        
        for idx, card in enumerate(match_cards):
            try:
                # Estrai competizione
                try:
                    comp_elem = card.find_element(By.CSS_SELECTOR, ".match-card__info--league p")
                    competition = comp_elem.text.strip()
                except:
                    competition = ""
                
                # Estrai round
                try:
                    round_elem = card.find_element(By.CSS_SELECTOR, ".match-card__info--league label")
                    round_text = round_elem.text.strip()
                except:
                    round_text = ""
                
                # Estrai data
                try:
                    date_elem = card.find_element(By.CSS_SELECTOR, ".match-card__info--match-time h3")
                    date_text = date_elem.text.strip()
                except:
                    date_text = ""
                
                # Estrai ora
                try:
                    time_elem = card.find_element(By.CSS_SELECTOR, ".match-card__info--match-time p")
                    time_text = time_elem.text.strip()
                except:
                    time_text = ""
                
                # Estrai squadre
                teams = []
                try:
                    team_imgs = card.find_elements(By.CSS_SELECTOR, ".match-card__teams--team picture img")
                    for img in team_imgs:
                        alt = img.get_attribute('alt')
                        if alt:
                            teams.append(alt.strip())
                except:
                    pass
                
                # Estrai score
                scores = []
                try:
                    score_spans = card.find_elements(By.CSS_SELECTOR, ".match-card__teams--score span")
                    for span in score_spans:
                        text = span.text.strip()
                        if text and text.isdigit():
                            scores.append(int(text))
                except:
                    pass
                
                # Estrai link
                match_center_link = None
                try:
                    link = card.find_element(By.CSS_SELECTOR, ".match-card__buttons a")
                    match_center_link = link.get_attribute('href')
                except:
                    pass
                
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
        
        logger.info(f"✅ Estratte {len(partite)} partite")
        return partite
        
    except Exception as e:
        logger.error(f"❌ Errore: {e}")
        return []
    finally:
        if driver:
            driver.quit()

@app.route('/')
def home():
    return jsonify({
        "status": "ok",
        "service": "API Calendario Palermo FC",
        "version": "3.0",
        "endpoints": {
            "/api/partite/casa": "Partite in casa",
            "/health": "Health check"
        }
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/partite/casa')
def get_partite_casa():
    try:
        logger.info("📥 Richiesta /api/partite/casa")
        partite = estrai_partite_palermo()
        
        if not partite:
            return jsonify({
                "success": False,
                "error": "Nessuna partita estratta",
                "count": 0,
                "data": []
            }), 500
        
        partite_casa = [p for p in partite if p.get('homeTeam') == 'Palermo']
        
        return jsonify({
            "success": True,
            "count": len(partite_casa),
            "data": partite_casa
        })
    except Exception as e:
        logger.error(f"❌ Errore: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
