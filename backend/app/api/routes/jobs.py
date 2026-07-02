"""
Job routes.

Jobs are private, scoped to whoever added them - the same ownership pattern
used for resumes. There's no shared/public pool: you add a posting because
you personally found it (e.g. copied from LinkedIn) and want to check your
resume's fit against it, the same way a tool like Jobscan works.

Routes:
POST   /jobs/           save a new job posting
GET    /jobs/           list all your jobs
GET    /jobs/{id}       get one job (404 if not yours)
DELETE /jobs/{id}       delete one job (404 if not yours)
"""
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreate, JobRead

router = APIRouter()


async def generate_and_save_job_embedding(job_id: int, text: str) -> None:
    """
    Background task: embed the job's text and write it back to the row.

    Imports are deliberately INSIDE this function, not at module level - same
    pattern used for resumes - so the ML stack doesn't get pulled in at
    import time and risk crashing uvicorn startup before the app is even up.
    """
    from app.database import AsyncSessionLocal
    from app.ml.inference import embed_text

    embedding = embed_text(text)
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is not None:
            job.embedding = embedding
            session.add(job)
            await session.commit()


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: JobCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Job:
    """
    Save a job posting.

    No duplicate check, this is a personal tool. The same company can post
    the same role in different cities or with different requirements. We trust
    the user to manage their own job list. If they add a duplicate by mistake
    they can delete it via DELETE /jobs/{id}.

    Required fields (title, company, description) are enforced automatically
    by JobCreate, an incomplete request never reaches this function body at
    all, Pydantic rejects it with 422 first.
    """
    # Create and save the job row first
    job = Job(
        user_id=current_user.id,
        title=body.title,
        company=body.company,
        description=body.description,
        requirements=body.requirements,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Embed the whole posting (title + company + description + requirements)
    # so matching considers all fields, not just the description.
    full_text = f"{job.title}\n{job.company}\n{job.description}\n{job.requirements}"
    background_tasks.add_task(generate_and_save_job_embedding, job.id, full_text)

    return job


@router.get("/", response_model=List[JobRead])
async def list_jobs(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[Job]:
    """Only the current user's own saved jobs - never anyone else's."""
    result = await session.execute(
        select(Job)
        .where(Job.user_id == current_user.id)
        .order_by(Job.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Job:
    """404 if the job doesn't exist OR belongs to someone else, same as resumes."""
    job = await session.get(Job, job_id)
    if job is None or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a job posting.

    204 No Content, means done, nothing to return.
    404 if the job doesn't exist or belongs to someone else.

    Use this to clean up accidental duplicates or jobs you no longer
    want to match against.
    """
    job = await session.get(Job, job_id)
    if job is None or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    await session.delete(job)
    await session.commit()