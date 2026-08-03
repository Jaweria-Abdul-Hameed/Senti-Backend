"""
security.py — everything auth-token related lives here so routers stay thin.

Covers three separate token concerns that all use the same JWT machinery
but different `purpose` claims so one can never be replayed as another:
  - "access"  : normal login session token, sent as `Authorization: Bearer <token>`
  - "reset"   : short-lived password-reset token (forgot-password flow)

Google Sign-In verification is also here since it's the other half of "auth".
"""

import datetime
import logging
import os
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import User, get_db

logger = logging.getLogger("senti.security")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days — mobile app, not a browser session
RESET_TOKEN_EXPIRE_MINUTES = 30

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if not SECRET_KEY:
    # Don't crash a dev server over this, but make it impossible to miss —
    # a default secret here would mean anyone can forge tokens for any user.
    logger.warning(
        "JWT_SECRET_KEY is not set in the environment! Generating a random "
        "one for this process only — every existing token/session will be "
        "invalidated on every restart. Set JWT_SECRET_KEY in your .env "
        "before this goes anywhere beyond your own machine."
    )
    import secrets
    SECRET_KEY = secrets.token_urlsafe(48)

_bearer_scheme = HTTPBearer(auto_error=False)


def _create_token(subject: str, purpose: str, expires_minutes: int) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": subject,
        "purpose": purpose,
        "iat": now,
        "exp": now + datetime.timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str, expected_purpose: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("purpose") != expected_purpose:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


# --- Access tokens (login sessions) ---

def create_access_token(user_id: int) -> str:
    return _create_token(subject=str(user_id), purpose="access", expires_minutes=ACCESS_TOKEN_EXPIRE_MINUTES)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Drop-in FastAPI dependency: `user: User = Depends(get_current_user)`.
    Every route that used to trust a client-supplied `user_id` query param
    should switch to this instead — the user_id now comes from a token only
    the server could have issued, not from whatever the client claims.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(credentials.credentials, expected_purpose="access")
    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user


# --- Password reset tokens ---

def create_password_reset_token(user_id: int) -> str:
    return _create_token(subject=str(user_id), purpose="reset", expires_minutes=RESET_TOKEN_EXPIRE_MINUTES)


def verify_password_reset_token(token: str) -> int:
    """Returns the user id the token was issued for, or raises HTTPException(401)."""
    payload = _decode_token(token, expected_purpose="reset")
    return int(payload["sub"])


# --- Google Sign-In ---

def verify_google_id_token(id_token_str: str) -> dict:
    """
    Verifies a Google ID token (obtained on-device via Credential Manager /
    Google Identity Services) and returns its claims (email, name, sub, etc).
    Raises HTTPException(401) if the token is invalid, expired, or wasn't
    issued for this app's client ID.

    Requires GOOGLE_CLIENT_ID in the environment — the *Web* client ID from
    Google Cloud Console (Credentials -> OAuth 2.0 Client IDs), used as the
    Android app's serverClientId when requesting a Google ID token. This is
    the standard "verify on your backend" setup; see
    https://developers.google.com/identity/sign-in/android/backend-auth
    """
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(
            status_code=500,
            detail="Server isn't configured for Google Sign-In yet (GOOGLE_CLIENT_ID missing).",
        )

    try:
        claims = google_id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), audience=client_id
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise HTTPException(status_code=401, detail="Invalid token issuer")

    return claims
