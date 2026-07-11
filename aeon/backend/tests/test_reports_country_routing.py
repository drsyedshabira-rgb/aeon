from app.api.v1.endpoints.reports import _resolve_authority_for_country


def test_resolve_authority_for_country_supports_pakistan():
    assert _resolve_authority_for_country(None, "PK") == "DRAP"


def test_resolve_authority_for_country_supports_us():
    assert _resolve_authority_for_country(None, "US") == "FDA"
