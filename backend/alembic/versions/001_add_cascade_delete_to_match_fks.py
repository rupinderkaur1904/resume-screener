"""add ondelete cascade to match foreign keys

Revision ID: 001
Revises:
Create Date: 2026-08-30
"""
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old FK constraints (Postgres default naming: table_column_fkey)
    op.drop_constraint("matches_resume_id_fkey", "matches", type_="foreignkey")
    op.drop_constraint("matches_job_id_fkey", "matches", type_="foreignkey")

    # Recreate with ON DELETE CASCADE
    op.create_foreign_key(
        "matches_resume_id_fkey", "matches", "resumes",
        ["resume_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "matches_job_id_fkey", "matches", "jobs",
        ["job_id"], ["id"], ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("matches_resume_id_fkey", "matches", type_="foreignkey")
    op.drop_constraint("matches_job_id_fkey", "matches", type_="foreignkey")

    op.create_foreign_key(
        "matches_resume_id_fkey", "matches", "resumes",
        ["resume_id"], ["id"],
    )
    op.create_foreign_key(
        "matches_job_id_fkey", "matches", "jobs",
        ["job_id"], ["id"],
    )
