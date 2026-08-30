"""Unit tests for app/core/security.py - pure functions, no DB/network needed."""
import pytest
import jwt

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_is_not_plaintext():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"


def test_verify_password_accepts_correct_password():
    hashed = hash_password("my-secret-pw")
    assert verify_password("my-secret-pw", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("my-secret-pw")
    assert verify_password("not-the-password", hashed) is False


def test_access_token_round_trip():
    token = create_access_token(subject=42)
    payload = decode_access_token(token)
    assert payload["sub"] == "42"


def test_expired_token_raises():
    import app.core.security as security_module

    # Mint a token with an expiry in the past directly, rather than waiting
    # for a real token to expire.
    token = jwt.encode(
        {"sub": "1", "exp": 0},  # exp in the past (epoch 0)
        security_module.settings.SECRET_KEY,
        algorithm=security_module.settings.ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)
