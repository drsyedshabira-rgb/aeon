"""
AEON — Vertical Slice MVP
Single-file FastAPI app implementing one end-to-end path:
  POST /process-text  ->  extract (spaCy + regex)  ->  map to FDA FAERS XML
                       ->  fake async submission (asyncio.create_task)
                       ->  status tracked in-memory (+ SQLite persistence)

Run:
  pip install -r requirements.txt
  python -m spacy download en_core_web_sm
  uvicorn aeon_vertical_slice:app --reload

Test:
  see test_curl_commands.txt
"""

import asyncio
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

import spacy
from fastapi import FastAPI, HTTPException
from jinja2 import Template
from pydantic import BaseModel

# --------------------------------------------------------------------------
# 0. App + DB setup
# --------------------------------------------------------------------------

app = FastAPI(title="AEON Vertical Slice MVP")

DB_PATH = "aeon_mvp.db"

# In-memory dict doubles as a fast-path cache; SQLite is the source of truth
# so state survives process restarts (useful even for a demo).
REPORTS: dict[str, dict] = {}


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS adr_reports (
                id TEXT PRIMARY KEY,
                pharmacy_id TEXT,
                raw_text TEXT,
                extracted_json TEXT,
                xml_payload TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


init_db()

# --------------------------------------------------------------------------
# 1. NLP extraction layer (app/nlp/extractor.py, inlined for the MVP)
# --------------------------------------------------------------------------

# spaCy is loaded once at startup. en_core_web_sm has no biomedical NER head,
# so it's used here mainly for sentence/token structure while the actual
# entity detection is regex/lexicon-based — this is an explicit MVP
# simplification, not a stand-in for the fine-tuned BioBERT model described
# in the full blueprint.
try:
    nlp = spacy.load("en_core_web_sm")
except OSError as exc:
    raise RuntimeError(
        "spaCy model 'en_core_web_sm' not found. Run: "
        "python -m spacy download en_core_web_sm"
    ) from exc

# Minimal lexicons — MVP scope only. Production version replaces these with
# RxNorm / ATC lookups (drugs) and a MedDRA term index (reactions), as noted
# in the blueprint's cartridge-engine section.
COMMON_ANTIBIOTICS = {
    "amoxicillin", "azithromycin", "ciprofloxacin", "doxycycline",
    "penicillin", "cephalexin", "clindamycin", "metronidazole",
    "levofloxacin", "erythromycin", "trimethoprim", "sulfamethoxazole",
    "vancomycin", "ampicillin", "clarithromycin", "gentamicin",
}

REACTION_KEYWORDS = {"rash", "nausea", "dizziness"}

AGE_PATTERN = re.compile(r"\b(\d{1,3})\s*(?:-|\s)?year(?:s)?[-\s]?old\b", re.IGNORECASE)
AGE_PATTERN_SHORT = re.compile(r"\bage[d]?\s*[:=]?\s*(\d{1,3})\b", re.IGNORECASE)
SEX_PATTERN = re.compile(r"\b(male|female|man|woman)\b", re.IGNORECASE)


class ADRExtractor:
    """
    MVP extractor: spaCy tokenization + regex/lexicon matching.
    Returns the canonical AEON schema fragment as defined in the blueprint:
      { suspect_drugs, reaction, patient_demographics, confidence }
    """

    def __init__(self, nlp_model):
        self.nlp = nlp_model

    def extract(self, raw_text: str) -> dict:
        doc = self.nlp(raw_text)
        tokens_lower = [tok.text.lower() for tok in doc]

        suspect_drugs = self._extract_drugs(tokens_lower, raw_text)
        reaction = self._extract_reaction(tokens_lower, raw_text)
        demographics = self._extract_demographics(raw_text)

        # Simple confidence heuristic for the MVP: fraction of the three
        # target fields that were actually populated. The full blueprint
        # uses per-entity NER confidence scores from the BERT model instead.
        found = [bool(suspect_drugs), bool(reaction.get("meddra_term")), bool(demographics)]
        confidence = round(sum(found) / len(found), 2)

        return {
            "suspect_drugs": suspect_drugs,
            "reaction": reaction,
            "patient_demographics": demographics,
            "confidence": confidence,
        }

    def _extract_drugs(self, tokens_lower: list[str], raw_text: str) -> list[dict]:
        found = []
        text_lower = raw_text.lower()
        for drug in COMMON_ANTIBIOTICS:
            if drug in text_lower:
                found.append({
                    "drug_name": drug.capitalize(),
                    "atc_code": None,   # would be resolved via RxNorm/ATC in production
                    "dose": None,
                    "route": None,
                })
        return found

    def _extract_reaction(self, tokens_lower: list[str], raw_text: str) -> dict:
        text_lower = raw_text.lower()
        matched_terms = [term for term in REACTION_KEYWORDS if term in text_lower]
        if not matched_terms:
            return {}
        return {
            "meddra_term": matched_terms[0],  # MVP: first match; production maps to nearest PT
            "all_terms_detected": matched_terms,
            "seriousness": "non-serious",      # MVP default; not inferred from context yet
            "outcome": "unknown",
        }

    def _extract_demographics(self, raw_text: str) -> dict:
        demographics = {}

        age_match = AGE_PATTERN.search(raw_text) or AGE_PATTERN_SHORT.search(raw_text)
        if age_match:
            demographics["age"] = age_match.group(1)

        sex_match = SEX_PATTERN.search(raw_text)
        if sex_match:
            raw_sex = sex_match.group(1).lower()
            demographics["sex"] = "male" if raw_sex in ("male", "man") else "female"

        return demographics


extractor = ADRExtractor(nlp)

# --------------------------------------------------------------------------
# 2. Regulatory Cartridge Engine — FDA FAERS cartridge hardcoded for MVP
# --------------------------------------------------------------------------

# This mirrors app/cartridges/fda_faers.json from the full blueprint,
# inlined here instead of loaded from a separate file for the MVP.
FDA_FAERS_CARTRIDGE = {
    "authority_code": "FDA",
    "country_code": "US",
    "version": "E2B-R3",
    "output_format": "xml",
}

FDA_XML_TEMPLATE = Template(
    """<?xml version="1.0" encoding="UTF-8"?>
<safetyreport>
    <authority>{{ authority_code }}</authority>
    <reportid>{{ report_id }}</reportid>
    <pharmacyid>{{ pharmacy_id }}</pharmacyid>
    <serious>{{ serious }}</serious>
    <patient>
        <patientagegroup>{{ age or "UNKNOWN" }}</patientagegroup>
        <patientsex>{{ sex or "UNKNOWN" }}</patientsex>
        {% for drug in drugs %}
        <drug>
            <medicinalproduct>{{ drug.drug_name }}</medicinalproduct>
            <drugdosagetext>{{ drug.dose or "NOT SPECIFIED" }}</drugdosagetext>
        </drug>
        {% endfor %}
        <reaction>
            <reactionmeddrapt>{{ reaction_term or "UNKNOWN" }}</reactionmeddrapt>
        </reaction>
    </patient>
    <narrative><![CDATA[{{ narrative }}]]></narrative>
</safetyreport>"""
)


def map_to_fda_faers_xml(report_id: str, pharmacy_id: str, extracted: dict, narrative: str) -> str:
    """
    app/cartridges/mapper.py, inlined.
    Maps the canonical AEON schema -> FDA FAERS-style XML per the
    fda_faers.json field_mapping defined in the blueprint.
    """
    demographics = extracted.get("patient_demographics", {})
    reaction = extracted.get("reaction", {})

    return FDA_XML_TEMPLATE.render(
        authority_code=FDA_FAERS_CARTRIDGE["authority_code"],
        report_id=report_id,
        pharmacy_id=pharmacy_id,
        serious="false" if reaction.get("seriousness") == "non-serious" else "unknown",
        age=demographics.get("age"),
        sex=demographics.get("sex"),
        drugs=extracted.get("suspect_drugs", []),
        reaction_term=reaction.get("meddra_term"),
        narrative=narrative,
    )

# --------------------------------------------------------------------------
# 3. Fake async submission worker (Celery stand-in for the MVP)
# --------------------------------------------------------------------------

async def submit_to_fda_fake(report_id: str, xml_payload: str):
    """
    Simulates app/workers/submission_worker.py without Celery/Redis.
    3-second delay, prints the XML, updates status to 'submitted'.
    """
    await asyncio.sleep(3)

    print("=== FDA SUBMISSION ===")
    print(xml_payload)
    print("=======================")

    now = datetime.now(timezone.utc).isoformat()

    if report_id in REPORTS:
        REPORTS[report_id]["status"] = "submitted"
        REPORTS[report_id]["updated_at"] = now

    with get_db() as conn:
        conn.execute(
            "UPDATE adr_reports SET status = ?, updated_at = ? WHERE id = ?",
            ("submitted", now, report_id),
        )

# --------------------------------------------------------------------------
# 4. API
# --------------------------------------------------------------------------

class ProcessTextRequest(BaseModel):
    text: str
    pharmacy_id: str = "demo"


class ProcessTextResponse(BaseModel):
    report_id: str
    status: str
    extracted: dict
    xml_payload: str


@app.post("/process-text", response_model=ProcessTextResponse)
async def process_text(payload: ProcessTextRequest):
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")

    report_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    extracted = extractor.extract(payload.text)
    xml_payload = map_to_fda_faers_xml(
        report_id=report_id,
        pharmacy_id=payload.pharmacy_id,
        extracted=extracted,
        narrative=payload.text,
    )

    record = {
        "id": report_id,
        "pharmacy_id": payload.pharmacy_id,
        "raw_text": payload.text,
        "extracted": extracted,
        "xml_payload": xml_payload,
        "status": "pending_submission",
        "created_at": now,
        "updated_at": now,
    }
    REPORTS[report_id] = record

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO adr_reports
                (id, pharmacy_id, raw_text, extracted_json, xml_payload, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                payload.pharmacy_id,
                payload.text,
                str(extracted),
                xml_payload,
                "pending_submission",
                now,
                now,
            ),
        )

    # Fire-and-forget async "submission" — MVP stand-in for the Celery worker
    asyncio.create_task(submit_to_fda_fake(report_id, xml_payload))

    return ProcessTextResponse(
        report_id=report_id,
        status="pending_submission",
        extracted=extracted,
        xml_payload=xml_payload,
    )


@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    if report_id not in REPORTS:
        raise HTTPException(status_code=404, detail="report not found")
    return REPORTS[report_id]


@app.get("/health")
async def health():
    return {"status": "ok"}
