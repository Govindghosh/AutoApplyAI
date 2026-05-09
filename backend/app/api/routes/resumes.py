import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.profile import Resume, UserProfile
from app.schemas.profile import ResumeResponse, ResumeApproveRequest
from app.services.profile_service import ProfileService
from app.services.resume_service import ResumeService
from app.workers.tasks import process_resume_task
from app.core.logging import logger

router = APIRouter(prefix="/profiles/resumes", tags=["resumes"])

UPLOAD_DIR = Path("storage/resumes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _resolve_profile(db: Session, user: User) -> UserProfile:
    profile = ProfileService.get_profile(db, user.id)
    if not profile:
        from app.schemas.profile import UserProfileCreate
        logger.info(f"Auto-creating profile for user {user.id} during resume upload")
        profile = ProfileService.create_profile(
            db,
            user.id,
            UserProfileCreate(
                full_name=user.email.split("@")[0],
                title="Awaiting Extraction...",
                skills=[],
            ),
        )
    return profile


def _assert_ownership(db: Session, resume: Resume, user_id: int) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.id == resume.profile_id).first()
    if not profile or profile.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return profile


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF, DOC, and DOCX files are supported.")

    contents = await file.read()
    if len(contents) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit.")

    profile = _resolve_profile(db, current_user)

    file_name = f"{uuid.uuid4()}{ext}"
    file_path = UPLOAD_DIR / file_name
    file_path.write_bytes(contents)

    # New upload becomes the base; demote existing ones
    db.query(Resume).filter(Resume.profile_id == profile.id).update({"is_base": False})

    db_resume = Resume(
        profile_id=profile.id,
        name=file.filename,
        file_path=str(file_path),
        content_text="",
        is_base=True,
        extraction_status="PENDING",
    )
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)

    process_resume_task.delay(db_resume.id, current_user.id)
    logger.info(f"Resume uploaded, extraction queued: resume_id={db_resume.id}")
    return {"status": "success", "resume_id": db_resume.id}


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    _assert_ownership(db, resume, current_user.id)
    return resume


@router.delete("/{resume_id}", status_code=204)
async def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    _assert_ownership(db, resume, current_user.id)

    # Remove file from disk if it exists
    if resume.file_path:
        try:
            Path(resume.file_path).unlink(missing_ok=True)
        except OSError:
            logger.warning(f"Could not delete file on disk: {resume.file_path}")

    # If deleting the base resume, promote the most recent remaining one
    was_base = resume.is_base
    db.delete(resume)
    db.commit()

    if was_base:
        next_base = (
            db.query(Resume)
            .filter(Resume.profile_id == resume.profile_id)
            .order_by(Resume.created_at.desc())
            .first()
        )
        if next_base:
            next_base.is_base = True
            db.commit()
            logger.info(f"Auto-promoted resume {next_base.id} to base after deletion")


@router.post("/{resume_id}/retry")
async def retry_extraction(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    _assert_ownership(db, resume, current_user.id)

    resume.extraction_status = "PENDING"
    resume.review_status = "NOT_STARTED"
    resume.extraction_data = None
    resume.confidence_scores = None
    db.commit()

    process_resume_task.delay(resume.id, current_user.id)
    logger.info(f"Resume extraction retry queued: resume_id={resume.id}")
    return {"status": "queued", "resume_id": resume.id}


@router.post("/{resume_id}/approve")
async def approve_extraction(
    resume_id: int,
    approve_data: ResumeApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    profile = _assert_ownership(db, resume, current_user.id)

    if not resume.extraction_data:
        raise HTTPException(status_code=400, detail="No extraction data to approve")

    filtered_data = {
        k: v for k, v in resume.extraction_data.items()
        if k in approve_data.approved_fields
    }
    ResumeService.sync_profile_from_resume(db, profile.id, filtered_data)

    resume.review_status = "REVIEWED"
    db.commit()

    logger.info(f"Resume {resume_id} extraction approved: fields={approve_data.approved_fields}")
    return {"status": "success", "synced_fields": approve_data.approved_fields}
