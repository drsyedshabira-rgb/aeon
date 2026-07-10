from app.cartridges.mapper import map_to_fda_faers_xml, load_cartridge


def test_fda_cartridge_loads_and_has_expected_shape():
    cartridge = load_cartridge("fda")
    assert cartridge["authority_code"] == "FDA"
    assert cartridge["status"] == "reference_only"
    assert "field_mapping" in cartridge


def test_map_to_fda_faers_xml_contains_expected_tags(sample_extracted):
    xml = map_to_fda_faers_xml(
        report_id="test-report-123",
        pharmacy_id="demo-pharmacy",
        extracted=sample_extracted,
        narrative="68 year old male developed a rash after amoxicillin",
    )

    assert "<safetyreport>" in xml
    assert "<reportid>test-report-123</reportid>" in xml
    assert "<medicinalproduct>Amoxicillin</medicinalproduct>" in xml
    assert "<reactionmeddrapt>rash</reactionmeddrapt>" in xml
    assert "<patientagegroup>68</patientagegroup>" in xml
    assert "<patientsex>male</patientsex>" in xml


def test_map_to_fda_faers_xml_handles_missing_fields():
    empty_extracted = {"suspect_drugs": [], "reaction": {}, "patient_demographics": {}}
    xml = map_to_fda_faers_xml("id-2", "pharmacy-2", empty_extracted, "no findings")

    assert "<patientagegroup>UNKNOWN</patientagegroup>" in xml
    assert "<reactionmeddrapt>UNKNOWN</reactionmeddrapt>" in xml
