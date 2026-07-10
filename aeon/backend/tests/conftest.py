import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base


@pytest.fixture(scope="function")
def test_db():
    """
    Uses an in-memory SQLite engine for fast unit tests. Note: JSONB and
    GIN indexes are Postgres-specific and won't be exercised by this
    fixture — integration tests against real Postgres (e.g. via a
    docker-compose test service) are needed to validate those.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def sample_extracted():
    return {
        "suspect_drugs": [{"drug_name": "Amoxicillin", "atc_code": None, "dose": None, "route": None}],
        "reaction": {"meddra_term": "rash", "all_terms_detected": ["rash"], "seriousness": "non-serious", "outcome": "unknown"},
        "patient_demographics": {"age": "68", "sex": "male"},
        "confidence": 1.0,
    }
