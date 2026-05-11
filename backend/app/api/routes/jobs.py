from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.services.job_service import JobFilters, JobService
from app.services.job_matching_service import JobMatchingService
from app.schemas.job import JobResponse, JobSourceSummary
from app.core.logging import logger
from app.api.deps import get_current_user
from app.models.job import JobStatus
from app.models.user import User

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=List[JobResponse])
def read_jobs(
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    status: JobStatus | None = None,
    source: str | None = None,
    location: str | None = None,
    remote_type: str | None = None,
    search: str | None = None,
    min_score: float | None = Query(default=None, ge=0, le=100),
    max_score: float | None = Query(default=None, ge=0, le=100),
    sort: str = "quality",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve jobs matching the user's base resume/domain profile.
    """
    return JobService.get_jobs_for_user(
        db,
        current_user.id,
        skip=skip,
        limit=limit,
        filters=JobFilters(
            status=status,
            source=source,
            location=location,
            remote_type=remote_type,
            search=search,
            min_score=min_score,
            max_score=max_score,
            sort=sort,
        ),
    )


@router.get("/sources", response_model=List[JobSourceSummary])
def read_job_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve supported job sources with resume-matched job counts.
    """
    return JobService.get_source_summary_for_user(db, current_user.id)


@router.get("/{job_id}", response_model=JobResponse)
def read_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a specific job by ID.
    """
    job = JobService.get_job(db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/scrape")
def trigger_scrape(current_user: User = Depends(get_current_user)):
    """
    Manually trigger the background scraping task for the user's domain.
    """
    from app.workers.tasks import scrape_jobs_task

    task = scrape_jobs_task.delay(current_user.id)
    logger.info(f"Triggered scraping task: {task.id}")
    return {"task_id": task.id, "status": "pending"}


@router.post("/{job_id}/analyze")
def analyze_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger AI analysis for a specific job.
    """
    from app.models.job import JobStatus
    from app.workers.tasks import analyze_job_task

    job = JobService.get_job(db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    match_context = JobMatchingService.build_context(db, current_user.id)
    if match_context.has_filter_signal and not JobMatchingService.matches(
        job, match_context
    ):
        raise HTTPException(
            status_code=400,
            detail="This job does not match your base resume/domain closely enough to analyze.",
        )

    job.status = JobStatus.ANALYSIS_PENDING
    job.analysis_error = None
    job.analysis_attempts = job.analysis_attempts or 0
    db.commit()

    task = analyze_job_task.delay(
        job_id,
        current_user.id,
        JobMatchingService.resume_text_for_analysis(match_context),
    )
    return {"task_id": task.id, "status": "pending", "job_status": job.status}


@router.post("/{job_id}/apply")
def apply_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger the application workflow for a shortlisted job.
    """
    job = JobService.get_job(db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from app.models.workflow import ApplicationWorkflow, WorkflowStatus
    from app.models.job import JobStatus
    from app.services.event_service import EventService, EventType
    from app.services.safety_throttle_service import SafetyThrottleService
    from app.services.state_manager import StateManager

    existing_workflow = (
        db.query(ApplicationWorkflow)
        .filter(
            ApplicationWorkflow.job_id == job_id,
            ApplicationWorkflow.user_id == current_user.id,
            ApplicationWorkflow.status.in_(
                [
                    WorkflowStatus.PENDING,
                    WorkflowStatus.RUNNING,
                    WorkflowStatus.PAUSED_FOR_HUMAN,
                ]
            ),
        )
        .first()
    )

    if existing_workflow:
        return {
            "task_id": None,
            "status": "already_active",
            "workflow_id": existing_workflow.id,
        }

    throttle = SafetyThrottleService.evaluate(db, current_user)
    if not throttle["allowed"]:
        EventService.emit(
            current_user.id,
            EventType.AUTOMATION_THROTTLED,
            {
                "job_id": job_id,
                "title": job.title,
                "blocked_reasons": throttle["blocked_reasons"],
                "daily_remaining": throttle["daily_remaining"],
                "concurrency_remaining": throttle["concurrency_remaining"],
            },
            resource_id=str(job_id),
        )
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Automation paused by beta safety limits.",
                "blocked_reasons": throttle["blocked_reasons"],
                "daily_remaining": throttle["daily_remaining"],
                "concurrency_remaining": throttle["concurrency_remaining"],
            },
        )

    if job.status != JobStatus.APPLYING:
        StateManager.transition_job(
            db,
            job,
            JobStatus.APPLYING,
            current_user.id,
            payload={"job_id": job_id, "title": job.title},
        )

    from app.workers.tasks import apply_to_job_task

    task = apply_to_job_task.delay(job_id, current_user.id)
    return {"task_id": task.id, "status": "pending", "workflow_id": None}


@router.post("/analyze-scraped")
def analyze_scraped_jobs(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Trigger AI analysis for scraped jobs and retry failed analyses.
    """
    from app.workers.tasks import analyze_job_task
    from app.models.job import Job, JobStatus

    match_context = JobMatchingService.build_context(db, current_user.id)
    queued_jobs = (
        db.query(Job)
        .filter(Job.status.in_([JobStatus.SCRAPED, JobStatus.ANALYSIS_FAILED]))
        .all()
    )
    relevant_jobs = JobMatchingService.filter_jobs(queued_jobs, match_context)
    resume_text = JobMatchingService.resume_text_for_analysis(match_context)

    task_ids = []
    for job in relevant_jobs:
        job.status = JobStatus.ANALYSIS_PENDING
        job.analysis_error = None
        job.analysis_attempts = job.analysis_attempts or 0
        db.commit()

        task = analyze_job_task.delay(job.id, current_user.id, resume_text)
        task_ids.append(task.id)

    return {
        "triggered_count": len(task_ids),
        "task_ids": task_ids,
        "filtered_out_count": len(queued_jobs) - len(relevant_jobs),
        "base_resume_id": match_context.base_resume_id,
        "domains": sorted(match_context.domains),
    }


@router.post("/{job_id}/finalize")
def finalize_application(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Approve the final submit checkpoint and resume the workflow.
    """
    from app.models.job import Job, JobStatus
    from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
    from app.services.state_manager import StateManager
    from app.services.workflow_orchestrator import WorkflowOrchestrator

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.APPLYING_PENDING_APPROVAL:
        raise HTTPException(
            status_code=400, detail="Job is not in pending approval state"
        )

    workflow = (
        db.query(ApplicationWorkflow)
        .filter(
            ApplicationWorkflow.job_id == job_id,
            ApplicationWorkflow.user_id == current_user.id,
            ApplicationWorkflow.status == WorkflowStatus.PAUSED_FOR_HUMAN,
        )
        .order_by(ApplicationWorkflow.created_at.desc())
        .first()
    )

    if not workflow:
        raise HTTPException(status_code=404, detail="Approval checkpoint not found")

    submit_step = (
        db.query(WorkflowStep)
        .filter(
            WorkflowStep.workflow_id == workflow.id,
            WorkflowStep.name == "SUBMIT_APPLICATION",
            WorkflowStep.status == WorkflowStatus.PAUSED_FOR_HUMAN,
        )
        .first()
    )

    if not submit_step:
        raise HTTPException(status_code=404, detail="Final submit checkpoint not found")

    WorkflowOrchestrator.complete_step(
        db,
        submit_step.id,
        {
            "approved_by_user": True,
            "approval_boundary": "final_submit",
        },
    )

    workflow.status = WorkflowStatus.RUNNING
    StateManager.transition_job(
        db,
        job,
        JobStatus.APPLYING,
        current_user.id,
        payload={"job_id": job_id, "workflow_id": workflow.id, "approved": True},
    )

    from app.workers.tasks import apply_to_job_task

    task = apply_to_job_task.delay(job_id, current_user.id)

    logger.info(f"Job {job_id} approved and workflow {workflow.id} resumed")
    return {
        "status": "resuming",
        "job_id": job_id,
        "workflow_id": workflow.id,
        "task_id": task.id,
        "new_status": job.status,
    }
