from unittest.mock import MagicMock, patch

from app.nlp.extractor import ADRExtractor


def make_fake_doc(tokens):
    fake_doc = MagicMock()
    fake_doc.__iter__.return_value = [MagicMock(text=t) for t in tokens]
    return fake_doc


def test_extract_drug_and_reaction_and_age():
    fake_nlp = MagicMock()
    fake_nlp.return_value = make_fake_doc(["68", "year", "old", "male", "developed", "a", "rash", "after", "amoxicillin"])

    extractor = ADRExtractor(nlp_model=fake_nlp)
    result = extractor.extract("68 year old male developed a rash after amoxicillin")

    assert result["suspect_drugs"] == [{"drug_name": "Amoxicillin", "atc_code": None, "dose": None, "route": None}]
    assert result["reaction"]["meddra_term"] == "rash"
    assert result["patient_demographics"]["age"] == "68"
    assert result["patient_demographics"]["sex"] == "male"
    assert result["confidence"] == 1.0


def test_extract_no_matches_returns_low_confidence():
    fake_nlp = MagicMock()
    fake_nlp.return_value = make_fake_doc(["patient", "called", "about", "refill"])

    extractor = ADRExtractor(nlp_model=fake_nlp)
    result = extractor.extract("patient called about refill")

    assert result["suspect_drugs"] == []
    assert result["reaction"] == {}
    assert result["confidence"] == 0.0


def test_extract_multiple_reactions_first_term_used():
    fake_nlp = MagicMock()
    fake_nlp.return_value = make_fake_doc(["nausea", "and", "dizziness", "after", "ciprofloxacin"])

    extractor = ADRExtractor(nlp_model=fake_nlp)
    result = extractor.extract("Patient reported nausea and dizziness after ciprofloxacin")

    assert set(result["reaction"]["all_terms_detected"]) == {"nausea", "dizziness"}
    assert result["reaction"]["meddra_term"] in {"nausea", "dizziness"}
