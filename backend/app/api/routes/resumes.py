"""
Resume routes.

POST   /resumes/upload      - upload a PDF, extract text, return 201 immediately,
                              generate embedding in the background
GET    /resumes/            - list all resumes belonging to the current user
GET    /resumes/{resume_id} - get one resume (404 if not owned by current user)
DELETE /resumes/{resume_id} - delete one resume (404 if not owned by current user)

Resumes are private, filtered by current_user.id everywhere. A resume that
exists but belongs to someone else returns 404, not 403, since 403 would
confirm to an attacker that the resume exists at all.

Embedding generation happens after the response is sent via BackgroundTasks,
so uploads return 201 immediately instead of making the user wait 1-2 seconds
for the ML model to run. raw_text and embedding are never sent to the
frontend; the ResumeRead schema filters them out automatically.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeRead
from app.services.pdf_parser import (
    extract_text_from_pdf,
    make_safe_filename,
    save_upload_to_disk,
    validate_upload,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

async def generate_and_save_embedding(resume_id: int, raw_text: str) -> None:
    """
    Background task: compute the embedding for a resume and persist it.

    This runs AFTER the upload response is already sent to the client.
    It opens its own DB session because the request's session is closed
    by the time this runs.

    Steps:
    1. embed_text() calls the ML model (already loaded in memory at startup)
    2. Open a fresh DB session
    3. Load the Resume row by id
    4. Set resume.embedding = the computed vector
    5. Commit and close

    If this fails (e.g. ML model issue), the resume row still exists in the
    DB with embedding=None. The user can see their resume but matching won't
    work until the embedding is populated. A production system would add a
    retry queue here.
    """
    from app.ml.inference import embed_text
    from app.database import AsyncSessionLocal

    embedding = embed_text(raw_text)

    async with AsyncSessionLocal() as session:
        resume = await session.get(Resume, resume_id)
        if resume:
            resume.embedding = embedding
            session.add(resume)
            await session.commit()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=ResumeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a resume PDF",
)
async def upload_resume(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Resume:
    """
    Upload a PDF resume: validate it, extract its text, save the file and DB
    row, and return 201 immediately. Embedding generation happens afterward
    in the background so the client never waits on the ML model.
    """
    file_bytes = await file.read()

    try:
        validate_upload(
            filename=file.filename,
            file_size_bytes=len(file_bytes),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    safe_filename = make_safe_filename(
        user_id=current_user.id,
        original_filename=file.filename,
    )
    raw_text = extract_text_from_pdf(file_bytes)
    file_path = save_upload_to_disk(file_bytes, safe_filename)

    resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        raw_text=raw_text,
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)

    # Runs after the response is already sent to the client.
    background_tasks.add_task(
        generate_and_save_embedding,
        resume_id=resume.id,
        raw_text=raw_text,
    )

    return resume


@router.get(
    "/",
    response_model=list[ResumeRead],
    summary="List all resumes belonging to the current user",
)
async def list_resumes(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Resume]:
    """
    Return all resumes uploaded by the currently logged-in user.
    Filtered by current_user.id, you only ever see YOUR resumes.
    Sorted newest first.
    """
    result = await session.execute(
        select(Resume).where(Resume.user_id == current_user.id)
    )
    all_resumes = list(result.scalars().all())
    all_resumes.sort(key=lambda r: r.created_at, reverse=True)
    return all_resumes


@router.get(
    "/{resume_id}",
    response_model=ResumeRead,
    summary="Get one resume by ID",
)
async def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Resume:
    """
    Fetch a single resume by its ID.
    404 if not found or belongs to a different user.
    """
    resume = await session.get(Resume, resume_id)

    if resume is None or resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    return resume


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a resume",
)
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a resume by ID.

    204 No Content, means done, nothing to return.
    404 if the resume doesn't exist or belongs to someone else.

    Use this to clean up old or duplicate resume uploads.
    """
    resume = await session.get(Resume, resume_id)

    if resume is None or resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    await session.delete(resume)
    await session.commit()