"""
Job model - a job posting the logged-in user is personally tracking (e.g.
copied from LinkedIn/Naukri) to check their resume's fit against. Private and
owned, exactly like Resume - there is no shared/public pool. Embedding is
computed the same way as for resumes so the two vector spaces are directly
comparable.
"""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.match import Match

EMBEDDING_DIM = 384


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    # Required, not nullable - every job always belongs to whoever added it,
    # same as Resume.user_id. No more "ownerless seeded job" case.
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)

    title: str = Field(nullable=False)
    company: str = Field(nullable=False)
    description: str = Field(nullable=False)
    requirements: str = Field(default="")  # free-text "must-have skills" block

    embedding: Optional[List[float]] = Field(
        default=None, sa_column=Column(Vector(EMBEDDING_DIM))
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)

    owner: "User" = Relationship(back_populates="jobs")
    matches: List["Match"] = Relationship(back_populates="job")