"""
Match model - the result of comparing one resume against one job: a 0-100 score
plus a structured explanation (matched skills, missing skills, etc.) so the
frontend can show *why* a score is what it is, not just the number.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlmodel import Column, Field, JSON, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.resume import Resume
    from app.models.job import Job


class Match(SQLModel, table=True):
    __tablename__ = "matches"

    id: Optional[int] = Field(default=None, primary_key=True)
    resume_id: int = Field(foreign_key="resumes.id", index=True, nullable=False)
    job_id: int = Field(foreign_key="jobs.id", index=True, nullable=False)

    score: float = Field(nullable=False)  # 0-100, see app/ml/inference.py
    # Example shape: {"matched_skills": [...], "missing_skills": [...], "summary": "..."}
    explanation: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)

    resume: "Resume" = Relationship(back_populates="matches")
    job: "Job" = Relationship(back_populates="matches")