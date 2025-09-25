from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

app = FastAPI(title="Baymax API", version="1.0.0")

# ---- Schemas ----
class Vitals(BaseModel):
    hr: Optional[float] = Field(None, description="Heart rate (bpm)")
    temp_c: Optional[float] = Field(None, description="Temperature in Celsius")
    sbp: Optional[float] = Field(None, description="Systolic blood pressure")
    spo2: Optional[float] = Field(None, description="Oxygen saturation %")

class TriageInput(BaseModel):
    age: Optional[int] = None
    symptoms: List[str] = Field(min_items=1)
    duration_hours: Optional[float] = None
    vitals: Optional[Vitals] = None
    allergies: Optional[List[str]] = None

class TriageResult(BaseModel):
    level: str
    red_flags: List[str] = []
    recommendation: str
    self_care_instructions: Optional[str] = None
    follow_up_hours: Optional[int] = None

class DDICheckInput(BaseModel):
    rxnorm_ids: List[str]
    fallback_names: Optional[List[str]] = []

class Interaction(BaseModel):
    pair: List[str]
    severity: str
    mechanism: Optional[str] = ""
    recommendation: str

class DDICheckResult(BaseModel):
    interactions: List[Interaction]
    unknown_names: List[str] = []

class EndSessionInput(BaseModel):
    user_phrase: str

class EndSessionResult(BaseModel):
    ended: bool
    message: str

# ---- Simple rule-based triage ----
EMERGENCY_TERMS = {"chest pain","shortness of breath","severe bleeding","confusion","stroke","numbness face","fainting","anaphylaxis","seizure"}
URGENT_TERMS = {"fever","worsening cough","rash spreading","moderate pain","vomiting","dehydration","wound infection"}

def triage_rules(payload: TriageInput) -> TriageResult:
    terms = {s.lower() for s in payload.symptoms}
    red_flags = []

    # Emergency checks
    if any(t in " ".join(terms) for t in EMERGENCY_TERMS):
        red_flags.append("Reported emergency symptom(s).")
    if payload.vitals and payload.vitals.spo2 is not None and payload.vitals.spo2 < 94:
        red_flags.append("SpO2 < 94%.")
    if payload.vitals and payload.vitals.sbp is not None and payload.vitals.sbp < 90:
        red_flags.append("Low systolic BP (<90).")
    if payload.vitals and payload.vitals.hr and payload.vitals.hr > 130:
        red_flags.append("Very high heart rate (>130).")

    if red_flags:
        return TriageResult(
            level="emergency",
            red_flags=red_flags,
            recommendation="Call emergency services now.",
            self_care_instructions=None,
            follow_up_hours=0
        )

    # Urgent
    if any(t in " ".join(terms) for t in URGENT_TERMS):
        return TriageResult(
            level="urgent_care",
            red_flags=[],
            recommendation="See a clinician today or within 24 hours.",
            self_care_instructions="Hydrate and rest until evaluated.",
            follow_up_hours=24
        )

    # Otherwise self-care
    return TriageResult(
        level="self_care",
        red_flags=[],
        recommendation="Self-care is reasonable.",
        self_care_instructions="Rest, hydrate, and monitor symptoms for changes.",
        follow_up_hours=48
    )

# ---- Mock DDI table (demo only) ----
DDI_TABLE = {
    ("sertraline","trazodone"): ("moderate","Additive serotonergic effects","Avoid combo if possible; monitor for serotonin syndrome."),
    ("ibuprofen","aspirin"): ("moderate","Additive GI bleeding risk","Avoid frequent combined use unless advised by clinician."),
    ("warfarin","ibuprofen"): ("major","Increased bleeding risk","Avoid; consult clinician for alternative analgesic.")
}

def normalize_names(names: List[str]) -> List[str]:
    return [n.strip().lower() for n in names if n and n.strip()]

# ---- Endpoints ----
@app.post("/triage-assess", response_model=TriageResult)
async def triage_assess(payload: TriageInput):
    return triage_rules(payload)

@app.post("/drug-interactions", response_model=DDICheckResult)
async def drug_interactions_check(payload: DDICheckInput):
    names = normalize_names(payload.fallback_names or [])
    # If rxnorm_ids provided, just pretend they map to names for demo
    if payload.rxnorm_ids and not names:
        names = [f"rxnorm:{rid}" for rid in payload.rxnorm_ids]

    interactions = []
    checked = set()
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            a, b = names[i], names[j]
            key = tuple(sorted((a,b)))
            if key in checked:
                continue
            checked.add(key)
            # Try direct names first
            info = DDI_TABLE.get(key)
            if not info:
                # Try stripping rxnorm: prefix if present
                k2 = tuple(sorted((a.replace("rxnorm:",""), b.replace("rxnorm:",""))))
                info = DDI_TABLE.get(k2)
            if info:
                severity, mechanism, rec = info
                interactions.append(Interaction(pair=[a,b], severity=severity, mechanism=mechanism, recommendation=rec))

    return DDICheckResult(interactions=interactions, unknown_names=[])

@app.get("/education-leaflet")
async def education_leaflet(topic: str = Query(..., min_length=1), reading_level: str = Query("basic")):
    t = topic.strip().lower()
    leaflets = {
        "asthma": {
            "title": "Asthma",
            "text": "Asthma affects the airways in your lungs, making them narrow and swollen. Use your rescue inhaler for sudden symptoms and avoid smoke and strong scents.",
            "key_points": ["Carry your rescue inhaler.", "See a clinician if you need your inhaler more than 2 days/week."],
            "sources": [{"name":"MedlinePlus","url":"https://medlineplus.gov/asthma.html"}]
        },
        "ibuprofen": {
            "title": "Ibuprofen",
            "text": "Ibuprofen is a pain and fever reducer (NSAID). Take with food. Do not combine routinely with other NSAIDs like aspirin unless advised.",
            "key_points": ["Max OTC dose 1200 mg/day unless directed.", "Stop and seek care for stomach bleeding signs."],
            "sources": [{"name":"DailyMed (Label)","url":"https://dailymed.nlm.nih.gov/"}]
        }
    }
    data = leaflets.get(t) or {"title": topic.title(), "text": f"Plain-language leaflet for '{topic}' not found. This is a demo endpoint.", "key_points": [], "sources": []}
    data["reading_level"] = "basic" if reading_level not in {"basic","standard"} else reading_level
    return JSONResponse(data)

@app.post("/end-session", response_model=EndSessionResult, responses={412: {"model": EndSessionResult}})
async def end_session(payload: EndSessionInput):
    phrase = (payload.user_phrase or "").strip().lower()
    if phrase == "i am satisfied with my care":
        return EndSessionResult(ended=True, message="Goodbye.")
    raise HTTPException(status_code=412, detail={"ended": False, "message": "Please say: I am satisfied with my care."})
