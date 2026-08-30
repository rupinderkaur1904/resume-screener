"""
Verify per-user ownership checks: User A's resources return 404 to User B.

Requires a running PostgreSQL instance AND a running FastAPI server.
Skipped in CI where no server is started (unit/migration tests cover the
logic; these are integration tests against the live Docker stack).

Run:
    cd backend && venv/Scripts/python.exe -m pytest tests/test_authorization.py -v
"""
import os
import httpx
import pytest

_DB_URL = os.environ.get(
    "MIGRATION_TEST_DB_URL",
    "postgresql+psycopg://resume_user:resume_pass@localhost:5432/resume_screener",
)

# Try to import psycopg; skip if unavailable
try:
    import psycopg  # noqa: F401
except ImportError:
    pytest.skip("psycopg not installed — skipping authorization tests", allow_module_level=True)

from sqlalchemy import create_engine, text

engine = create_engine(_DB_URL)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = os.environ.get("AUTH_TEST_BASE_URL", "http://localhost:9000")

# Minimal valid PDF with extractable text (required after C11 empty-text check)
# This PDF has a text stream so extract_text_from_pdf returns non-empty text.
_MINIMAL_PDF = (
    b"%PDF-1.0\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 200 200]/Parent 2 0 R"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 44>>stream\n"
    b"BT /F1 12 Tf 10 100 Td (test resume) Tj ET\n"
    b"endstream\nendobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000228 00000 n \n"
    b"0000000324 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\n"
    b"startxref\n418\n%%EOF\n"
)


def _register(email: str, password: str = "password123") -> httpx.Response:
    return httpx.post(f"{_BASE}/auth/register", json={
        "email": email, "password": password, "full_name": email.split("@")[0],
    }, timeout=10)


def _login(email: str, password: str = "password123") -> str:
    resp = httpx.post(f"{_BASE}/auth/login", json={
        "email": email, "password": password,
    }, timeout=10)
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _cleanup_user(email: str):
    """Delete user and their owned resources directly via SQL."""
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM matches WHERE resume_id IN "
                         "(SELECT id FROM resumes WHERE user_id = "
                         "(SELECT id FROM users WHERE email = :e))"), {"e": email})
        conn.execute(text("DELETE FROM matches WHERE job_id IN "
                         "(SELECT id FROM jobs WHERE user_id = "
                         "(SELECT id FROM users WHERE email = :e))"), {"e": email})
        conn.execute(text("DELETE FROM resumes WHERE user_id = "
                         "(SELECT id FROM users WHERE email = :e)"), {"e": email})
        conn.execute(text("DELETE FROM jobs WHERE user_id = "
                         "(SELECT id FROM users WHERE email = :e)"), {"e": email})
        conn.execute(text("DELETE FROM users WHERE email = :e"), {"e": email})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# Skip all tests in this module if no live server is reachable.
# In CI there is no FastAPI server — these are integration tests.
@pytest.fixture(autouse=True, scope="module")
def _require_live_server():
    try:
        httpx.get(f"{_BASE}/health", timeout=3)
    except httpx.ConnectError:
        pytest.skip("No live server at {_BASE} — skipping integration tests")


class TestResumeAuthorization:
    def test_user_b_cannot_read_user_a_resume(self):
        email_a = "auth_test_a_resume@example.com"
        email_b = "auth_test_b_resume@example.com"
        _cleanup_user(email_a)
        _cleanup_user(email_b)
        try:
            _register(email_a)
            _register(email_b)
            token_a = _login(email_a)
            token_b = _login(email_b)

            # User A uploads a resume
            resp = httpx.post(
                f"{_BASE}/resumes/upload",
                headers=_auth(token_a),
                files={"file": ("resume.pdf", _MINIMAL_PDF, "application/pdf")},
                timeout=10,
            )
            assert resp.status_code == 201, resp.text
            resume_id = resp.json()["id"]

            # User B tries to read it → 404
            resp = httpx.get(
                f"{_BASE}/resumes/{resume_id}",
                headers=_auth(token_b),
                timeout=10,
            )
            assert resp.status_code == 404

            # User B tries to delete it → 404
            resp = httpx.delete(
                f"{_BASE}/resumes/{resume_id}",
                headers=_auth(token_b),
                timeout=10,
            )
            assert resp.status_code == 404
        finally:
            _cleanup_user(email_a)
            _cleanup_user(email_b)

    def test_user_b_cannot_list_user_a_resumes(self):
        email_a = "auth_test_a_list@example.com"
        email_b = "auth_test_b_list@example.com"
        _cleanup_user(email_a)
        _cleanup_user(email_b)
        try:
            _register(email_a)
            _register(email_b)
            token_a = _login(email_a)
            token_b = _login(email_b)

            # User A uploads a resume
            httpx.post(
                f"{_BASE}/resumes/upload",
                headers=_auth(token_a),
                files={"file": ("resume.pdf", _MINIMAL_PDF, "application/pdf")},
                timeout=10,
            )

            # User B lists resumes → should see 0 (not User A's)
            resp = httpx.get(f"{_BASE}/resumes/", headers=_auth(token_b), timeout=10)
            assert resp.status_code == 200
            assert len(resp.json()) == 0
        finally:
            _cleanup_user(email_a)
            _cleanup_user(email_b)


class TestJobAuthorization:
    def test_user_b_cannot_read_user_a_job(self):
        email_a = "auth_test_a_job@example.com"
        email_b = "auth_test_b_job@example.com"
        _cleanup_user(email_a)
        _cleanup_user(email_b)
        try:
            _register(email_a)
            _register(email_b)
            token_a = _login(email_a)
            token_b = _login(email_b)

            # User A creates a job
            resp = httpx.post(
                f"{_BASE}/jobs/",
                headers=_auth(token_a),
                json={"title": "Engineer", "company": "Acme", "description": "Python dev"},
                timeout=10,
            )
            assert resp.status_code == 201, resp.text
            job_id = resp.json()["id"]

            # User B tries to read it → 404
            resp = httpx.get(
                f"{_BASE}/jobs/{job_id}",
                headers=_auth(token_b),
                timeout=10,
            )
            assert resp.status_code == 404

            # User B tries to delete it → 404
            resp = httpx.delete(
                f"{_BASE}/jobs/{job_id}",
                headers=_auth(token_b),
                timeout=10,
            )
            assert resp.status_code == 404
        finally:
            _cleanup_user(email_a)
            _cleanup_user(email_b)


class TestMatchAuthorization:
    def test_user_b_cannot_match_with_user_a_resume(self):
        email_a = "auth_test_a_match@example.com"
        email_b = "auth_test_b_match@example.com"
        _cleanup_user(email_a)
        _cleanup_user(email_b)
        try:
            _register(email_a)
            _register(email_b)
            token_a = _login(email_a)
            token_b = _login(email_b)

            # User A uploads a resume
            resp = httpx.post(
                f"{_BASE}/resumes/upload",
                headers=_auth(token_a),
                files={"file": ("resume.pdf", _MINIMAL_PDF, "application/pdf")},
                timeout=10,
            )
            resume_id = resp.json()["id"]

            # User B tries to use User A's resume for matching → 404
            resp = httpx.post(
                f"{_BASE}/matches/compute?resume_id={resume_id}",
                headers=_auth(token_b),
                timeout=10,
            )
            assert resp.status_code == 404
        finally:
            _cleanup_user(email_a)
            _cleanup_user(email_b)
