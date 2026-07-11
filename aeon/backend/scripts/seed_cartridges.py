"""
Seeds all 10 cartridges into regulatory_cartridges. Loads directly from
the JSON files in app/cartridges/ so the DB always matches what's on disk.
Non-FDA cartridges are seeded with is_active=False by default, since they
are unverified drafts and should not be selectable for real submission
until reviewed — see app/cartridges/README.md.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.base import SessionLocal
from app.models.cartridge import RegulatoryCartridge

CARTRIDGE_DIR = Path(__file__).resolve().parents[1] / "app" / "cartridges"
CARTRIDGE_FILES = [
    "fda_faers.json", "ema_eudravigilance.json", "mhra_yellowcard.json",
    "tga_daen.json", "pmda.json", "healthcanada.json", "anvisa.json",
    "cdsco.json", "nmpa.json", "who_vigibase.json", "pakistan.json",
]


def seed():
    db = SessionLocal()
    try:
        for filename in CARTRIDGE_FILES:
            with open(CARTRIDGE_DIR / filename) as f:
                data = json.load(f)

            exists = db.query(RegulatoryCartridge).filter(
                RegulatoryCartridge.authority_code == data["authority_code"],
                RegulatoryCartridge.version == data["version"],
            ).first()
            if exists:
                continue

            is_reference_or_verified = data.get("status") in ("reference_only", "verified")

            db.add(RegulatoryCartridge(
                authority_code=data["authority_code"],
                country_code=data["country_code"] if len(data["country_code"]) == 2 else "XX",
                version=data["version"],
                field_mapping=data["field_mapping"],
                submission_endpoint=data.get("submission_endpoint"),
                is_active=is_reference_or_verified,  # non-FDA drafts seeded inactive
            ))
            print(f"Seeded {data['authority_code']} (active={is_reference_or_verified})")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
