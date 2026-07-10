from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models.base import get_db
from app.models.user import User
from app.models.organization import Organization
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


def _authenticate_and_issue_token(username: str, password: str, db: Session) -> TokenResponse:
    """
    Shared auth logic used by both /token (OAuth2 form) and /login (JSON).
    Kept as a plain function taking plain args — not a FastAPI dependency
    reconstruction — so neither endpoint has to fake the other's request shape.
    """
    user = db.query(User).filter(User.email == username).first()
    if not user or not verify_password(password, user.hashed_password):
        # Same error for "no such user" and "wrong password" — do not reveal
        # which one it was, that leaks whether an email is registered.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "org": str(org.id) if org else None,
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.post("/token", response_model=TokenResponse)
def login_oauth2_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2-compatible token endpoint (form-encoded body)."""
    return _authenticate_and_issue_token(form_data.username, form_data.password, db)


@router.post("/login", response_model=TokenResponse)
def login_json(login_data: LoginRequest, db: Session = Depends(get_db)):
    """JSON-body login endpoint, same logic as /token, no form reconstruction."""
    return _authenticate_and_issue_token(login_data.username, login_data.password, db)
