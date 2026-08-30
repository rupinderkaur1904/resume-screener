"""
Match routes.

POST /matches/compute?resume_id=XX

    Scores one resume against all of the current user's jobs in a single
    vectorized call, persists the results to the matches table, and returns
    a ranked list of {job_id, title, company, score, explanation}.

Design notes:
- Batch matching only: compute_match_scores_batch() does one vectorized
  comparison instead of looping and scoring each job individually.
- Jobs without an embedding yet (background task still running) are
  skipped rather than causing an error.
- The resume must belong to the current user, 404 otherwise, same rule
  as GET /resumes/{id}.
- Old matches for this resume are replaced on each call, so re-running
  a match after adding new jobs doesn't leave stale duplicate rows.
"""
import re
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.ml.inference import compute_match_scores_batch
from app.models.job import Job
from app.models.match import Match
from app.models.resume import Resume
from app.models.user import User
from app.schemas.match import MatchComputeResponse, MatchResult

router = APIRouter()

# Common English stopwords to ignore in keyword overlap.
_STOPWORDS = frozenset(
    "a an the and or but if in on at to for of is are was were be been being "
    "has have had do does did will would shall should may might can could "
    "this that these those it its he she they them we you i my our their "
    "am "
    "with from by as not no nor so yet both each every all any few more "
    "most other some such than too very just about also after before between "
    "into through during without above below up down out off over under again "
    "further then once here there when where why how what which who whom how "
    "must need able work working experience skills years using use used "
    "good strong excellent great".split()
)


def _tokenize(text: str) -> Counter:
    """Lowercase-tokenize *text* into a word frequency counter, ignoring stopwords."""
    tokens = re.findall(r"[a-z0-9+#]+", text.lower())
    return Counter(t for t in tokens if t not in _STOPWORDS and len(t) > 1)


def _build_explanation(
    resume_text: str, job_text: str, score: float
) -> dict:
    """
    Compute a lightweight keyword-overlap explanation between a resume and
    a job posting. Returns a dict with ``matched_skills``, ``missing_skills``,
    and ``summary``.
    """
    resume_tokens = _tokenize(resume_text)
    job_tokens = _tokenize(job_text)

    matched = sorted(set(resume_tokens) & set(job_tokens))
    missing = sorted(set(job_tokens) - set(resume_tokens))

    return {
        "matched_skills": matched[:20],
        "missing_skills": missing[:20],
        "summary": f"Your resume is a {score:.1f}% match for this role.",
    }



@router.post(
    "/compute",
    response_model=MatchComputeResponse,
    summary="Match a resume against all your saved jobs",
)
async def compute_matches(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MatchComputeResponse:
    """
    Score resume_id against every job the current user has saved, save the
    results, and return them ranked by score descending.
    """
    resume = await session.get(Resume, resume_id)
    if resume is None or resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    if resume.embedding is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume embedding is not ready yet. Please wait a moment and try again.",
        )

    result = await session.execute(
        select(Job).where(Job.user_id == current_user.id)
    )
    all_jobs = result.scalars().all()

    # Skip jobs whose embedding hasn't finished computing yet.
    jobs_with_embeddings = [j for j in all_jobs if j.embedding is not None]

    if not jobs_with_embeddings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No jobs with embeddings found. Please add some jobs first and wait for them to process.",
        )

    job_embeddings = [j.embedding for j in jobs_with_embeddings]
    scores = await run_in_threadpool(
        compute_match_scores_batch,
        resume_embedding=resume.embedding,
        job_embeddings=job_embeddings,
    )

    results = []
    for job, score in zip(jobs_with_embeddings, scores):
        job_text = f"{job.title} {job.company} {job.description} {job.requirements}"
        explanation = _build_explanation(
            resume_text=resume.raw_text,
            job_text=job_text,
            score=score,
        )
        results.append(
            MatchResult(
                job_id=job.id,
                title=job.title,
                company=job.company,
                score=score,
                explanation=explanation,
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)

    # Replace any previous matches for this resume so history doesn't
    # accumulate stale duplicates every time the user re-runs a match.
    existing = await session.execute(
        select(Match).where(Match.resume_id == resume_id)
    )
    for old_match in existing.scalars().all():
        await session.delete(old_match)

    for r in results:
        session.add(
            Match(
                resume_id=resume_id,
                job_id=r.job_id,
                score=r.score,
                explanation=r.explanation,
            )
        )
    await session.commit()

    return MatchComputeResponse(
        resume_id=resume_id,
        total_jobs=len(results),
        results=results,
    )
