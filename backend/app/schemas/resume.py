"""
Pydantic schemas for the resume API.

Why this file exists separately from models/resume.py:
- models/resume.py  = what PostgreSQL stores (everything including raw_text,
                       embedding, parsed_skills)
- schemas/resume.py = what the API sends back to the frontend (filtered view)

The frontend never needs raw_text (could be thousands of words) or embedding
(384 raw numbers) or parsed_skills (internal processing artifact). Sending them
would waste bandwidth and leak internal implementation details.

from_attributes=True tells Pydantic: "read fields directly from the SQLModel
object's attributes instead of expecting a plain dictionary."
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ResumeRead(BaseModel):
    """
    What the frontend receives after upload, or when listing resumes.

    Deliberately excludes:
    - raw_text      (internal, could be huge)
    - embedding     (internal, 384 numbers frontend can't use)
    - parsed_skills (internal processing artifact)
    """
    id: int
    user_id: int
    filename: str
    file_path: str
    created_at: datetime

    model_config = {"from_attributes": True}