"""
Importing every model module here means a single `from app import models` (used in
database.py's init_db) registers all four tables on SQLModel.metadata - you won't
silently lose a table just because nothing else happened to import it first.
"""
from app.models.user import User
from app.models.resume import Resume
from app.models.job import Job
from app.models.match import Match

__all__ = ["User", "Resume", "Job", "Match"]