# Palermo FC Calendar API

API automatica per estrarre il calendario delle partite del Palermo FC dalla stagione 2025-26.

## 🚀 Endpoints

### Base URL
```
https://palermo-calendar-api.onrender.com
```

### 📍 Endpoints Disponibili

#### 1. Home / Info API
```
GET /
```
Ritorna informazioni sull'API e gli endpoint disponibili.

#### 2. Tutte le Partite
```
GET /api/partite
```
Ritorna tutte le partite del Palermo (casa + trasferta).

**Risposta:**
```json
{
  "success": true,
  "count": 38,
  "data": [
    {
      "id": 1,
      "competition": "Serie BKT",
      "round": "1ª",
      "date": "2025-08-16",
      "time": "20:30",
      "homeTeam": "Brescia",
      "awayTeam": "Palermo",
      "homeScore": 1,
      "awayScore": 0,
      "status": "finished",
      "matchCenter": "https://..."
    }
    // ... altre partite
  ],
  "timestamp": "2025-02-02T10:30:00"
}
```

#### 3. Partite in Casa
```
GET /api/partite/casa
```
Ritorna solo le partite dove il Palermo gioca in casa (homeTeam = "Palermo").

#### 4. Partite in Trasferta ✨ NUOVO
```
GET /api/partite/trasferta
```
Ritorna solo le partite dove il Palermo gioca in trasferta (awayTeam = "Palermo").

#### 5. Health Check
```
GET /health
```
Verifica lo stato del server.

**Risposta:**
```json
{
  "status": "ok",
  "timestamp": "2025-02-02T10:30:00"
}
```

---

## 🛠️ Tecnologie

- **Python 3.11**
- **Flask** - Framework web
- **Flask-CORS** - Gestione CORS
- **requests-html** - Web scraping con JavaScript rendering
- **Playwright** - Browser automation per rendering JavaScript
- **Gunicorn** - WSGI HTTP Server

---

## 📦 Installazione Locale

### Prerequisiti
- Python 3.11+
- pip

### Passi

1. **Clona il repository**
```bash
git clone https://github.com/Gae93/palermo-calendar-api.git
cd palermo-calendar-api
```

2. **Crea un virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate
```

3. **Installa le dipendenze**
```bash
pip install -r requirements.txt
playwright install chromium
playwright install-deps
```

4. **Avvia il server**
```bash
python app.py
```

5. **Testa l'API**
```bash
curl http://localhost:5000/api/partite/casa
curl http://localhost:5000/api/partite/trasferta
```

---

## 🚢 Deploy su Render

### Deploy Automatico da GitHub

1. **Push del codice su GitHub**
```bash
git add .
git commit -m "Aggiunto endpoint trasferta"
git push
```

2. **Render farà automaticamente il redeploy**
   - Grazie al file `render.yaml` configurato
   - Il deploy richiede 2-3 minuti
   - I log sono visibili nella dashboard di Render

---

## 📊 Struttura Dati Partita

```javascript
{
  "id": 1,                      // ID progressivo
  "competition": "Serie BKT",   // Nome competizione
  "round": "1ª",                // Giornata
  "date": "2025-08-16",         // Data (YYYY-MM-DD)
  "time": "20:30",              // Orario (HH:MM)
  "homeTeam": "Brescia",        // Squadra casa
  "awayTeam": "Palermo",        // Squadra trasferta
  "homeScore": 1,               // Gol casa (solo se finita)
  "awayScore": 0,               // Gol trasferta (solo se finita)
  "status": "finished",         // "scheduled" | "finished"
  "matchCenter": "https://..."  // Link al match center (opzionale)
}
```

---

## 🔄 Come Funziona

1. L'API fa scraping della pagina ufficiale del Palermo FC
2. Simula il click sul pulsante "Tutte" per caricare tutte le partite
3. Estrae i dati dalle card delle partite
4. Filtra in base all'endpoint richiesto:
   - `/casa` → homeTeam == "Palermo"
   - `/trasferta` → awayTeam == "Palermo"
   - `/partite` → tutte le partite

---

## ⚡ Performance e Limiti

- **Tempo di risposta**: ~5-10 secondi (a causa del rendering JavaScript)
- **Timeout**: 120 secondi configurati su Gunicorn
- **Cache**: Nessuna cache implementata (ogni richiesta fa scraping live)
- **Rate limiting**: Nessun limite impostato

### Piano Free di Render
- **Sleep**: Il servizio va in sleep dopo 15 minuti di inattività
- **Riattivazione**: Prima richiesta dopo sleep: ~30-60 secondi
- **Soluzione**: Usa un keep-alive service o passa al piano pagato

---

## 🐛 Troubleshooting

### Errore "Impossibile estrarre partite"
- Verifica che il sito del Palermo FC sia online
- Controlla i log su Render per dettagli
- Potrebbe essere un cambiamento nella struttura HTML del sito

### Timeout errors
- Il rendering JavaScript richiede tempo
- Se persiste, aumenta il timeout in `Procfile`:
  ```
  web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 180
  ```

### Build fails su Render
- Verifica che `playwright install chromium` sia nel `buildCommand`
- Controlla che tutte le dipendenze siano in `requirements.txt`

---

## 📝 Changelog

### v3.1 (2025-02-02)
- ✨ Aggiunto endpoint `/api/partite/trasferta`
- 📝 Documentazione aggiornata

### v3.0
- 🎯 Implementato click automatico su "Tutte" le partite
- 🔧 Migliorato il rendering JavaScript

---

## 📄 Licenza

MIT License - Sentiti libero di usare e modificare questo codice.

---

## 📧 Supporto

Per problemi o domande, apri una issue su GitHub.
