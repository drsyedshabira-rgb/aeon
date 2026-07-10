"""
DEV-ONLY: mints a JWT for local testing without a real login endpoint.
Run inside the backend container: python scripts/mint_dev_token.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import create_access_token
from app.models.base import SessionLocal
from app.models.user import User

db = SessionLocal()
user = db.query(User).filter(User.email == "admin@aeon.local").first()
db.close()

if not user:
    print("Demo user not found — run scripts/seed_demo_data.py first.")
    sys.exit(1)

token = create_access_token({
    "sub": str(user.id),
    "role": user.role,
    "org": str(user.organization_id),
})
print(token)
