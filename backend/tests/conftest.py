"""
Shared pytest fixtures. Sets the minimum required env vars before any app
module is imported, since Settings() requires DATABASE_URL and SECRET_KEY
with no defaults.
"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
