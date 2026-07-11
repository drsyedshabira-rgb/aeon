"""
app/cartridges/mapper.py

Generic cartridge-driven mapper: given a cartridge's field_mapping and an
extracted AEON-schema dict, produce the target authority's payload.

The FDA FAERS XML generation is lifted directly from the validated
aeon_vertical_slice.py MVP (same Jinja2 template, unchanged), per the
binding rule. Other authorities reuse the same rendering approach but
their field_mapping content is DRAFT/UNVERIFIED — see cartridges/README.md.
"""

import json
from pathlib import Path

from jinja2 import Template

CARTRIDGE_DIR = Path(__file__).parent

# --- FDA FAERS: unchanged from the validated MVP ---------------------------

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

DRAP_XML_TEMPLATE = Template(
    """<?xml version="1.0" encoding="UTF-8"?>
<drappayload>
    <authority>{{ authority_code }}</authority>
    <reportid>{{ report_id }}</reportid>
    <pharmacyid>{{ pharmacy_id }}</pharmacyid>
    <reporttype>yellow_form</reporttype>
    <seriousness>{{ seriousness or "unknown" }}</seriousness>
    <patient>
        <age>{{ age or "UNKNOWN" }}</age>
        <sex>{{ sex or "UNKNOWN" }}</sex>
    </patient>
    <medicines>
        {% for drug in drugs %}
        <medicine>
            <name>{{ drug.drug_name }}</name>
            <dose>{{ drug.dose or "NOT SPECIFIED" }}</dose>
        </medicine>
        {% endfor %}
    </medicines>
    <reaction>{{ reaction_term or "UNKNOWN" }}</reaction>
    <narrative><![CDATA[{{ narrative }}]]></narrative>
</drappayload>"""
)


def load_cartridge(authority_code: str) -> dict:
    normalized = authority_code.strip().lower()

    candidates = [
        f"{normalized}.json",
        f"{normalized}_faers.json",
    ]

    if normalized == "drap":
        candidates.append("pakistan.json")

    for filename in candidates:
        path = CARTRIDGE_DIR / filename
        if path.exists():
            with open(path) as f:
                return json.load(f)

    raise FileNotFoundError(f"No cartridge found for authority: {authority_code}")


def map_to_fda_faers_xml(report_id: str, pharmacy_id: str, extracted: dict, narrative: str) -> str:
    demographics = extracted.get("patient_demographics", {})
    reaction = extracted.get("reaction", {})

    return FDA_XML_TEMPLATE.render(
        authority_code="FDA",
        report_id=report_id,
        pharmacy_id=pharmacy_id,
        serious="false" if reaction.get("seriousness") == "non-serious" else "unknown",
        age=demographics.get("age"),
        sex=demographics.get("sex"),
        drugs=extracted.get("suspect_drugs", []),
        reaction_term=reaction.get("meddra_term"),
        narrative=narrative,
    )


def map_to_drap_xml(report_id: str, pharmacy_id: str, extracted: dict, narrative: str) -> str:
    demographics = extracted.get("patient_demographics", {})
    reaction = extracted.get("reaction", {})

    return DRAP_XML_TEMPLATE.render(
        authority_code="DRAP",
        report_id=report_id,
        pharmacy_id=pharmacy_id,
        seriousness=reaction.get("seriousness", "unknown"),
        age=demographics.get("age"),
        sex=demographics.get("sex"),
        drugs=extracted.get("suspect_drugs", []),
        reaction_term=reaction.get("meddra_term"),
        narrative=narrative,
    )


def map_report(authority_code: str, report_id: str, pharmacy_id: str, extracted: dict, narrative: str) -> dict:
    """
    Dispatches to the correct mapper for the given authority.
    FDA has a verified, working mapper. DRAP now has a structural XML
    mapper for placeholder/mock integration testing.
    """
    cartridge = load_cartridge(authority_code)

    if authority_code.upper() == "FDA":
        payload = map_to_fda_faers_xml(report_id, pharmacy_id, extracted, narrative)
        return {"format": "xml", "payload": payload, "cartridge_version": cartridge["version"]}

    if authority_code.upper() == "DRAP":
        payload = map_to_drap_xml(report_id, pharmacy_id, extracted, narrative)
        return {"format": "xml", "payload": payload, "cartridge_version": cartridge["version"]}

    raise NotImplementedError(
        f"Cartridge for {authority_code} is a structural DRAFT only — "
        f"its field_mapping has not been verified against {authority_code}'s "
        f"actual published submission spec. Do not use for real submissions. "
        f"See app/cartridges/README.md."
    )
