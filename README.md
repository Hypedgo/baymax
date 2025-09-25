# Baymax API (FastAPI)

A minimal Baymax-style healthcare companion API with four endpoints:

- `POST /triage-assess` – rule-based symptom triage (self_care / urgent_care / emergency)
- `POST /drug-interactions` – simple mock drug–drug interaction checker (uses names or RxNorm IDs)
- `GET /education-leaflet?topic=asthma&reading_level=basic` – plain-language leaflet for conditions/meds
- `POST /end-session` – ends a session only when user says “I am satisfied with my care”

This repo is meant for:
- Connecting **ChatGPT Actions** via your OpenAPI schema
- Quick deployment to **Render.com** (free tier works)

## Quick start (local)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Open http://127.0.0.1:8000/docs for Swagger UI.

## Deploy to Render

1. Push this repo to GitHub.
2. In **Render**, create a **Web Service** from your repo.
3. Select environment **Python 3.x** (default).
4. Build command (Render auto-detects from `requirements.txt`). Leave blank or set:
   ```
   pip install -r requirements.txt
   ```
5. Start command:
   ```
   uvicorn app:app --host 0.0.0.0 --port $PORT
   ```
6. Save. Render will build and deploy. Your service URL will be something like:
   `https://your-baymax.onrender.com`

Tip: This repo includes `render.yaml` so you can use the **Blueprint** deploy too.

## Endpoints

### POST /triage-assess
**Body**
```json
{
  "age": 42,
  "symptoms": ["chest pain","shortness of breath","nausea"],
  "duration_hours": 1.2,
  "vitals": { "hr": 110, "temp_c": 36.9, "sbp": 138, "spo2": 93 },
  "allergies": ["penicillin"]
}
```
**Response**
```json
{
  "level": "emergency",
  "red_flags": ["Chest pain + shortness of breath", "SpO2 < 94%"],
  "recommendation": "Call emergency services now.",
  "self_care_instructions": null,
  "follow_up_hours": 0
}
```

### POST /drug-interactions
**Body**
```json
{
  "rxnorm_ids": ["617314","1049630"],
  "fallback_names": ["sertraline","trazodone"]
}
```

### GET /education-leaflet
Query params: `topic`, optional `reading_level` (basic|standard).

### POST /end-session
**Body**
```json
{ "user_phrase": "I am satisfied with my care" }
```

## Disclaimer
This API is for educational/demo purposes only and **not** a substitute for professional medical advice. Do not use for real triage or diagnosis.
