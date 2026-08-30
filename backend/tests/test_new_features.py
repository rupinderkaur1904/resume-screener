"""Tests for new validations and features added in this pass."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.limiter import limiter
from app.database import get_session
from app.schemas.user import RegisterRequest
from app.services.pdf_parser import validate_upload


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_limiter():
    """Reset the shared limiter state before every test so rate-limit counts
    never leak across tests."""
    limiter.reset()
    yield
    limiter.reset()


# ---------------------------------------------------------------------------
# Rate limiter regression (P1-2)
# ---------------------------------------------------------------------------

def test_login_rate_limit_blocks_after_five_attempts():
    """POST /auth/login is limited to 5/minute.  The 6th call must return 429.

    We build a tiny FastAPI app with only the auth router so we never hit the
    database or load the ML model — this test stays fast and dependency-free.
    The DB session is mocked so get_user_by_email returns None (no user found),
    which makes every login attempt return 401 — the correct pre-rate-limit
    response.  Only the 6th attempt should get 429.
    """
    from app.api.routes.auth import router

    # Build a mock session: execute().scalars().first() returns None → no user
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def _mock_session():
        yield mock_session

    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(router, prefix="/auth")
    app.dependency_overrides[get_session] = _mock_session

    client = TestClient(app, raise_server_exceptions=False)

    payload = {"email": "nobody@example.com", "password": "wrong"}

    for i in range(5):
        resp = client.post("/auth/login", json=payload)
        assert resp.status_code == 401, f"attempt {i + 1} should be 401"

    # 6th attempt — rate limit kicks in
    resp = client.post("/auth/login", json=payload)
    assert resp.status_code == 429, (
        f"expected 429 (rate limited) on 6th attempt, got {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# P1-3: Password minimum length
# ---------------------------------------------------------------------------

def test_register_rejects_short_password():
    with pytest.raises(ValueError, match="at least 8 characters"):
        RegisterRequest(email="a@b.com", password="short", full_name="Test")


def test_register_accepts_8_char_password():
    req = RegisterRequest(email="a@b.com", password="12345678", full_name="Test")
    assert req.password == "12345678"


def test_register_accepts_long_password_under_72_bytes():
    pw = "a" * 72
    req = RegisterRequest(email="a@b.com", password=pw, full_name="Test")
    assert len(req.password) == 72


# ---------------------------------------------------------------------------
# P1-5: PDF magic bytes
# ---------------------------------------------------------------------------

def test_validate_upload_rejects_non_pdf_bytes():
    with pytest.raises(ValueError, match="magic bytes"):
        validate_upload("resume.pdf", 100, file_bytes=b"NOT A PDF FILE")


def test_validate_upload_accepts_pdf_magic_bytes():
    validate_upload("resume.pdf", 100, file_bytes=b"%PDF-1.4 some content")


def test_validate_upload_without_file_bytes_skips_magic_check():
    # No file_bytes passed — old callers still work without the magic byte check
    validate_upload("resume.pdf", 100, file_bytes=None)


# ---------------------------------------------------------------------------
# P3-11: Keyword overlap explanation (imports production function)
# ---------------------------------------------------------------------------
from app.api.routes.matches import _tokenize, _build_explanation


def test_tokenize_basic():
    tokens = _tokenize("Python developer with React experience")
    assert "python" in tokens
    assert "developer" in tokens
    assert "react" in tokens


def test_tokenize_skips_stopwords():
    tokens = _tokenize("I am a software engineer")
    assert "am" not in tokens
    assert "a" not in tokens
    assert "software" in tokens
    assert "engineer" in tokens


def test_build_explanation_populates_skills():
    resume = "Python developer with Django REST and PostgreSQL experience"
    job = "Looking for a Python developer with React and PostgreSQL"
    explanation = _build_explanation(resume, job, 75.5)

    assert "matched_skills" in explanation
    assert "missing_skills" in explanation
    assert "summary" in explanation
    assert "75.5%" in explanation["summary"]
    assert "python" in explanation["matched_skills"]
    assert "postgresql" in explanation["matched_skills"]
    assert "react" in explanation["missing_skills"]


def test_build_explanation_empty_texts():
    explanation = _build_explanation("", "", 0.0)
    assert explanation["matched_skills"] == []
    assert explanation["missing_skills"] == []


# ---------------------------------------------------------------------------
# C10: Embedding failure sets status to failed
# ---------------------------------------------------------------------------

import asyncio
from unittest.mock import patch, AsyncMock, MagicMock


def test_resume_embedding_failure_sets_status_failed():
    """When embed_text raises, the background task sets embedding_status='failed'."""
    mock_resume = MagicMock()
    mock_resume.embedding_status = "pending"

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_resume)

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.ml.inference.embed_text", side_effect=RuntimeError("model crash")), \
         patch("app.database.AsyncSessionLocal", mock_session_factory):
        # Import inside the patch context so the local `from ... import embed_text`
        # inside generate_and_save_embedding picks up the mocked version.
        from app.api.routes.resumes import generate_and_save_embedding
        asyncio.run(generate_and_save_embedding(resume_id=1, raw_text="test"))

    assert mock_resume.embedding_status == "failed"
    mock_session.commit.assert_called()


def test_job_embedding_failure_sets_status_failed():
    """When embed_text raises, the job background task sets embedding_status='failed'."""
    mock_job = MagicMock()
    mock_job.embedding_status = "pending"

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_job)

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.ml.inference.embed_text", side_effect=RuntimeError("model crash")), \
         patch("app.database.AsyncSessionLocal", mock_session_factory):
        from app.api.routes.jobs import generate_and_save_job_embedding
        asyncio.run(generate_and_save_job_embedding(job_id=1, text="test"))

    assert mock_job.embedding_status == "failed"
    mock_session.commit.assert_called()
