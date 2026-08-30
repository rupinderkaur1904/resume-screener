"""
Pydantic schemas for the match API.

Why this file exists separately from models/match.py:
- models/match.py  = what PostgreSQL stores (resume_id, job_id, score, explanation)
- schemas/match.py = what the API sends back to the frontend

MatchResult is what POST /matches/compute returns, one entry per job,
ranked by score descending. It includes enough job detail so the frontend
can display a meaningful ranked list without making extra API calls.

We deliberately include job title and company inline here (denormalized)
so the frontend gets everything it needs in one response.
"""
from typing import Optional

from pydantic import BaseModel


class MatchResult(BaseModel):
    """
    One job's match result, returned as part of the ranked list
    from POST /matches/compute.

    score is 0-100:
        90-100 = excellent match
        70-89  = good match
        50-69  = partial match
        below 50 = weak match
    """
    job_id: int
    title: str
    company: str
    score: float
    explanation: Optional[dict] = None

    model_config = {"from_attributes": True}


class MatchComputeResponse(BaseModel):
    """
    Full response from POST /matches/compute.

    resume_id   = which resume was matched
    total_jobs  = how many jobs were scored
    results     = ranked list of MatchResult, highest score first
    """
    resume_id: int
    total_jobs: int
    results: list[MatchResult]