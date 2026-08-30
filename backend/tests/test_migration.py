"""
Verify the 001_add_cascade_delete_to_match_fks migration in both directions.

Calls the real upgrade()/downgrade() functions from the migration file,
with Alembic's op bound to a connection so it operates on isolated tables.

Requires a running PostgreSQL instance (Docker db on localhost:5432).

Run:
    cd backend && venv/Scripts/python.exe -m pytest tests/test_migration.py -v
"""
import importlib.util
import os
import sys
import textwrap

import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Docker Postgres
# ---------------------------------------------------------------------------
_DB_URL = os.environ.get(
    "MIGRATION_TEST_DB_URL",
    "postgresql+psycopg://resume_user:resume_pass@localhost:5432/resume_screener",
)

try:
    import psycopg  # noqa: F401
except ImportError:
    pytest.skip("psycopg not installed — skipping migration tests",
                allow_module_level=True)

engine = create_engine(_DB_URL)

# Unique table names avoid colliding with the real app tables.
# The migration always targets the public schema, so we create
# uniquely-named tables and drop them after each test.
_CREATE_TABLES_SQL = textwrap.dedent("""\
    CREATE TABLE mig_test_users (
        id SERIAL PRIMARY KEY,
        email VARCHAR NOT NULL UNIQUE,
        hashed_password VARCHAR NOT NULL,
        full_name VARCHAR NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP NOT NULL DEFAULT now()
    );
    CREATE TABLE mig_test_resumes (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES mig_test_users(id),
        filename VARCHAR NOT NULL,
        file_path VARCHAR NOT NULL,
        raw_text TEXT DEFAULT '',
        created_at TIMESTAMP NOT NULL DEFAULT now()
    );
    CREATE TABLE mig_test_jobs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES mig_test_users(id),
        title VARCHAR NOT NULL,
        company VARCHAR NOT NULL,
        description VARCHAR NOT NULL,
        requirements TEXT DEFAULT '',
        created_at TIMESTAMP NOT NULL DEFAULT now()
    );
    CREATE TABLE mig_test_matches (
        id SERIAL PRIMARY KEY,
        resume_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,
        score DOUBLE PRECISION NOT NULL,
        explanation JSON,
        created_at TIMESTAMP NOT NULL DEFAULT now(),
        CONSTRAINT matches_resume_id_fkey FOREIGN KEY (resume_id)
            REFERENCES mig_test_resumes(id),
        CONSTRAINT matches_job_id_fkey FOREIGN KEY (job_id)
            REFERENCES mig_test_jobs(id)
    );
""")

_DROP_TABLES_SQL = textwrap.dedent("""\
    DROP TABLE IF EXISTS mig_test_matches CASCADE;
    DROP TABLE IF EXISTS mig_test_jobs CASCADE;
    DROP TABLE IF EXISTS mig_test_resumes CASCADE;
    DROP TABLE IF EXISTS mig_test_users CASCADE;
""")

# The real migration targets table names "resumes", "jobs", "matches".
# We redirect these to our uniquely-named test tables.
_TABLE_RENAME_MAP = {
    "resumes": "mig_test_resumes",
    "jobs": "mig_test_jobs",
    "matches": "mig_test_matches",
    "users": "mig_test_users",
}


def _get_cascade_status():
    """Query pg_constraint (the authoritative source) for FK delete rules
    on mig_test_matches.  Returns a dict of constraint_name -> bool (is_cascade).
    """
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT conname, pg_get_constraintdef(oid) AS defn "
            "FROM pg_constraint "
            "WHERE conrelid = 'mig_test_matches'::regclass "
            "AND contype = 'f'"
        ))
        return {
            row[0]: "ON DELETE CASCADE" in row[1]
            for row in result
        }


# ---------------------------------------------------------------------------
# Alembic op binding
# ---------------------------------------------------------------------------

def _load_migration_module():
    """Load the real migration file, evicting any cached version first."""
    mod_name = "migration_001"
    sys.modules.pop(mod_name, None)

    migration_path = os.path.join(
        os.path.dirname(__file__), "..", "alembic", "versions",
        "001_add_cascade_delete_to_match_fks.py",
    )
    spec = importlib.util.spec_from_file_location(mod_name, migration_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _patch_op_for_test_tables():
    """Intercept op calls to redirect from real table names to test tables.

    Handles drop_constraint, create_foreign_key, add_column, drop_column.
    """
    import alembic.op as op_module

    _orig_drop_constraint = op_module.drop_constraint
    _orig_create_fk = op_module.create_foreign_key
    _orig_add_column = op_module.add_column
    _orig_drop_column = op_module.drop_column

    def patched_drop_constraint(constraint_name, table_name, type_=None, **kw):
        real_table = _TABLE_RENAME_MAP.get(table_name, table_name)
        return _orig_drop_constraint(constraint_name, real_table, type_=type_, **kw)

    def patched_create_fk(constraint_name, source, referent, local_cols,
                          remote_cols, **kw):
        real_source = _TABLE_RENAME_MAP.get(source, source)
        real_referent = _TABLE_RENAME_MAP.get(referent, referent)
        return _orig_create_fk(constraint_name, real_source, real_referent,
                               local_cols, remote_cols, **kw)

    def patched_add_column(table_name, column, **kw):
        real_table = _TABLE_RENAME_MAP.get(table_name, table_name)
        return _orig_add_column(real_table, column, **kw)

    def patched_drop_column(table_name, column_name, **kw):
        real_table = _TABLE_RENAME_MAP.get(table_name, table_name)
        return _orig_drop_column(real_table, column_name, **kw)

    op_module.drop_constraint = patched_drop_constraint
    op_module.create_foreign_key = patched_create_fk
    op_module.add_column = patched_add_column
    op_module.drop_column = patched_drop_column
    return _orig_drop_constraint, _orig_create_fk, _orig_add_column, _orig_drop_column


def _restore_op(origs):
    """Restore the original op functions."""
    import alembic.op as op_module
    op_module.drop_constraint = origs[0]
    op_module.create_foreign_key = origs[1]
    op_module.add_column = origs[2]
    op_module.drop_column = origs[3]


@pytest.fixture()
def _alembic_context():
    """Yield (connection, ops) with alembic op patched to use test table names.

    The caller MUST commit conn after running the migration so that
    queries from other connections can see the results (PostgreSQL transaction
    isolation).
    """
    conn = engine.connect()
    ctx = MigrationContext.configure(conn)
    ops = Operations(ctx)
    ops._install_proxy()

    origs = _patch_op_for_test_tables()

    yield conn, ops

    _restore_op(origs)
    ops._remove_proxy()
    conn.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _setup_and_teardown():
    """Create fresh test tables before each test; drop them after."""
    with engine.begin() as conn:
        conn.execute(text(_DROP_TABLES_SQL))
        conn.execute(text(_CREATE_TABLES_SQL))
    yield
    with engine.begin() as conn:
        conn.execute(text(_DROP_TABLES_SQL))


def test_upgrade_adds_cascade_constraints(_alembic_context):
    """upgrade() should replace FKs with ON DELETE CASCADE."""
    conn, ops = _alembic_context
    migration = _load_migration_module()
    migration.upgrade()
    conn.commit()

    rules = _get_cascade_status()
    assert "matches_resume_id_fkey" in rules, f"missing resume FK: {rules}"
    assert "matches_job_id_fkey" in rules, f"missing job FK: {rules}"
    assert rules["matches_resume_id_fkey"], (
        f"resume FK should be CASCADE, got: {rules}"
    )
    assert rules["matches_job_id_fkey"], (
        f"job FK should be CASCADE, got: {rules}"
    )


def test_downgrade_removes_cascade_constraints(_alembic_context):
    """upgrade() then downgrade() should revert FKs to NO ACTION."""
    conn, ops = _alembic_context
    migration = _load_migration_module()
    migration.upgrade()
    migration.downgrade()
    conn.commit()

    rules = _get_cascade_status()
    assert not rules.get("matches_resume_id_fkey", False), (
        f"resume FK should NOT be CASCADE after downgrade: {rules}"
    )
    assert not rules.get("matches_job_id_fkey", False), (
        f"job FK should NOT be CASCADE after downgrade: {rules}"
    )


# ---------------------------------------------------------------------------
# Migration 002: add embedding_status to resumes and jobs
# ---------------------------------------------------------------------------

def _load_migration_002():
    """Load migration 002 by file path."""
    mod_name = "migration_002"
    sys.modules.pop(mod_name, None)

    migration_path = os.path.join(
        os.path.dirname(__file__), "..", "alembic", "versions",
        "002_add_embedding_status.py",
    )
    spec = importlib.util.spec_from_file_location(mod_name, migration_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _get_column_names(table_name: str) -> set:
    """Return the set of column names for a given table."""
    with engine.connect() as conn:
        result = conn.execute(text(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{table_name}' AND table_schema = 'public'"
        ))
        return {row[0] for row in result}


def test_migration_002_adds_embedding_status(_alembic_context):
    """Migration 002 should add embedding_status column to resumes and jobs."""
    conn, ops = _alembic_context

    # First run migration 001 (prerequisite)
    migration_001 = _load_migration_module()
    migration_001.upgrade()

    # Verify embedding_status does NOT exist yet
    resume_cols = _get_column_names("mig_test_resumes")
    job_cols = _get_column_names("mig_test_jobs")
    assert "embedding_status" not in resume_cols
    assert "embedding_status" not in job_cols

    # Run migration 002
    migration_002 = _load_migration_002()
    migration_002.upgrade()
    conn.commit()

    # Verify embedding_status now exists
    resume_cols = _get_column_names("mig_test_resumes")
    job_cols = _get_column_names("mig_test_jobs")
    assert "embedding_status" in resume_cols, f"missing in resumes: {resume_cols}"
    assert "embedding_status" in job_cols, f"missing in jobs: {job_cols}"


def test_migration_002_downgrade_removes_embedding_status(_alembic_context):
    """Migration 002 downgrade should remove embedding_status column."""
    conn, ops = _alembic_context

    migration_001 = _load_migration_module()
    migration_001.upgrade()

    migration_002 = _load_migration_002()
    migration_002.upgrade()
    conn.commit()

    # Verify it exists
    assert "embedding_status" in _get_column_names("mig_test_resumes")

    # Downgrade migration 002
    migration_002.downgrade()
    conn.commit()

    # Verify it's gone
    resume_cols = _get_column_names("mig_test_resumes")
    job_cols = _get_column_names("mig_test_jobs")
    assert "embedding_status" not in resume_cols, f"still present after downgrade: {resume_cols}"
    assert "embedding_status" not in job_cols, f"still present after downgrade: {job_cols}"
