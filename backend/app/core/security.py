"""
Security helpers: password hashing and JWT creation/verification.

Kept as pure functions (no FastAPI, no DB) so they can be unit-tested without
spinning up the app. FastAPI-specific wiring (reading the Authorization
header, querying the DB) lives in app/api/deps.py.

Uses PyJWT rather than python-jose, which has been dormant since 2022 and
carries unpatched CVEs.
"""
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*. Store this, never the raw password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored bcrypt *hashed* value."""
    return _pwd_context.verify(plain, hashed)


def create_access_token(subject: str | int) -> str:
    """
    Mint a signed HS256 JWT whose *sub* claim is the user's ID.

    The ID goes in *sub* rather than the email so that an email change never
    invalidates an existing token, and it's the value get_current_user()
    needs for the DB lookup anyway.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Verify signature and expiry, then return the decoded payload dict.

    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    The caller (get_current_user in deps.py) converts these to HTTP 401s;
    this module never imports FastAPI.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
