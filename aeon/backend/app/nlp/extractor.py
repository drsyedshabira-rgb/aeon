"""
app/nlp/extractor.py

Lifted directly from the validated aeon_vertical_slice.py MVP, per the
binding rule to preserve the extraction logic exactly. Only change from
the MVP: wrapped for import into the layered app structure, and added
OCRTextExtractor as a real (stubbed) class rather than inline.

NOTE ON SCOPE: this remains the MVP's spaCy-tokenization + regex/lexicon
extractor, NOT the fine-tuned BioBERT NER model described in the original
blueprint's Section 3. Swapping in a real BioBERT model is a separate,
substantial ML workstream (data labeling, fine-tuning, evaluation) — it
is not a drop-in replacement and is intentionally out of scope here.
"""

import re

import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError as exc:
    raise RuntimeError(
        "spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm"
    ) from exc

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
    def __init__(self, nlp_model=nlp):
        self.nlp = nlp_model

    def extract(self, raw_text: str) -> dict:
        doc = self.nlp(raw_text)
        tokens_lower = [tok.text.lower() for tok in doc]

        suspect_drugs = self._extract_drugs(tokens_lower, raw_text)
        reaction = self._extract_reaction(tokens_lower, raw_text)
        demographics = self._extract_demographics(raw_text)

        found = [bool(suspect_drugs), bool(reaction.get("meddra_term")), bool(demographics)]
        confidence = round(sum(found) / len(found), 2)

        return {
            "suspect_drugs": suspect_drugs,
            "reaction": reaction,
            "patient_demographics": demographics,
            "confidence": confidence,
        }

    def _extract_drugs(self, tokens_lower: list, raw_text: str) -> list:
        found = []
        text_lower = raw_text.lower()
        for drug in COMMON_ANTIBIOTICS:
            if drug in text_lower:
                found.append({
                    "drug_name": drug.capitalize(),
                    "atc_code": None,
                    "dose": None,
                    "route": None,
                })
        return found

    def _extract_reaction(self, tokens_lower: list, raw_text: str) -> dict:
        text_lower = raw_text.lower()
        matched_terms = [term for term in REACTION_KEYWORDS if term in text_lower]
        if not matched_terms:
            return {}
        return {
            "meddra_term": matched_terms[0],
            "all_terms_detected": matched_terms,
            "seriousness": "non-serious",
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


class OCRTextExtractor:
    """
    Image -> text, using pytesseract server-side (client-side Tesseract.js
    handles the offline PWA path separately — see frontend/lib/offline).
    """
    def extract_text_from_image(self, image_bytes: bytes) -> str:
        import io
        from PIL import Image
        import pytesseract

        image = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(image)


extractor = ADRExtractor()
ocr_extractor = OCRTextExtractor()
