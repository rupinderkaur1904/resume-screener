"""
Pydantic schemas for job CRUD.

JobCreate is what the client sends when saving a job posting they want to
track and match their resume against. JobRead is what comes back: it adds
server-generated fields (id, user_id, created_at) and excludes `embedding`
(384 raw numbers, meaningless to the client and never displayed).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class JobCreate(BaseModel):
    title: str
    company: str
    description: str
    requirements: str = ""  # optional - defaults to empty if not provided


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # lets this build directly from a Job ORM row

    id: int
    user_id: int
    title: str
    company: str
    description: str
    requirements: str
    created_at: datetime