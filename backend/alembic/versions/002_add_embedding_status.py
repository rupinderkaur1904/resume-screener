"""add embedding_status to resumes and jobs

Revision ID: 002
Revises: 001
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resumes",
        sa.Column("embedding_status", sa.String(), nullable=False, server_default="pending"),
    )
    op.add_column(
        "jobs",
        sa.Column("embedding_status", sa.String(), nullable=False, server_default="pending"),
    )


def downgrade() -> None:
    op.drop_column("jobs", "embedding_status")
    op.drop_column("resumes", "embedding_status")
