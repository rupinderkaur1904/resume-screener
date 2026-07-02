"""
User model - a registered account. The same table serves both "job seekers"
(who upload resumes) and "recruiters" (who post jobs) - kept simple for the MVP;
a `role` field can be added later if you want to separate permissions properly.
"""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.resume import Resume
    from app.models.job import Job


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)  # NEVER store plaintext - see core/security.py
    full_name: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # One user -> many resumes uploaded
    resumes: List["Resume"] = Relationship(back_populates="owner")
    # One user -> many jobs they're personally tracking (private, like resumes)
    jobs: List["Job"] = Relationship(back_populates="owner")