"""
Resume model - one row per uploaded PDF. Stores the parsed text and, once the
background embedding task runs, a dense vector representation used for matching.

We use pgvector (Postgres extension + Python package) instead of a plain
ARRAY(Float) column because it gives us native vector indexes (HNSW/IVFFlat)
and a `<=>` cosine-distance operator directly in SQL, instead of pulling
every row into Python to compute similarity manually.
"""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlmodel import Column, Field, JSON, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.match import Match

EMBEDDING_DIM = 384  # output size of all-MiniLM-L6-v2; keep in sync with app/config.py


class Resume(SQLModel, table=True):
    __tablename__ = "resumes"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)

    filename: str = Field(nullable=False)          # original filename, for display
    file_path: str = Field(nullable=False)          # actual path inside the uploads volume
    raw_text: str = Field(default="")                # full text extracted via PyMuPDF
    parsed_skills: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Populated asynchronously after upload by the background task in
    # api/routes/resumes.py (calls app.ml.inference.embed_text).
    # Nullable because the row exists before the embedding finishes computing.
    embedding: Optional[List[float]] = Field(
        default=None, sa_column=Column(Vector(EMBEDDING_DIM))
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)

    owner: "User" = Relationship(back_populates="resumes")
    matches: List["Match"] = Relationship(back_populates="resume")
