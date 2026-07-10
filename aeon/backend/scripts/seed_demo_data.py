"""
Seeds one demo organization + one admin user for local development only.
NEVER run this against a production database — the password is a
well-known placeholder.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.base import SessionLocal
from app.models.organization import Organization
from app.models.user import User
from app.core.security import hash_password


def seed():
    db = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.name == "Demo Pharmacy").first()
        if not org:
            org = Organization(name="Demo Pharmacy", country_code="US", plan="starter")
            db.add(org)
            db.commit()
            db.refresh(org)

        existing_admin = db.query(User).filter(User.email == "admin@aeon.local").first()
        if not existing_admin:
            db.add(User(
                organization_id=org.id,
                email="admin@aeon.local",
                hashed_password=hash_password("password123"),
                role="admin",
            ))
            print("Seeded admin user (DEV ONLY — do not use in production)")
        else:
            print("Admin user already exists, skipping")

        # Second user for RBAC testing — confirms a 'pharmacist' role can hit
        # /reports but gets a 403 on admin-only routes like /cartridges.
        existing_pharmacist = db.query(User).filter(User.email == "pharmacist@aeon.local").first()
        if not existing_pharmacist:
            db.add(User(
                organization_id=org.id,
                email="pharmacist@aeon.local",
                hashed_password=hash_password("password123"),
                role="pharmacist",
            ))
            print("Seeded pharmacist user (DEV ONLY — do not use in production)")
        else:
            print("Pharmacist user already exists, skipping")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
