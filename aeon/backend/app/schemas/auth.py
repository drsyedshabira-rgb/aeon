from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str  # email address
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until token expires
