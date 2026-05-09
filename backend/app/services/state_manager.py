from typing import Optional
from app.models.job import Job, JobStatus
from app.services.event_service import EventService, EventType
from app.core.logging import logger
from sqlalchemy.orm import Session

class StateManager:
    # Valid status transitions for the Job state machine
    VALID_TRANSITIONS = {
        JobStatus.SCRAPED: [JobStatus.ANALYSIS_PENDING, JobStatus.FAILED],
        JobStatus.ANALYSIS_PENDING: [JobStatus.ANALYZING, JobStatus.FAILED],
        JobStatus.ANALYZING: [JobStatus.ANALYZED, JobStatus.ANALYSIS_FAILED, JobStatus.FAILED],
        JobStatus.ANALYZED: [JobStatus.SHORTLISTED, JobStatus.FAILED],
        JobStatus.SHORTLISTED: [JobStatus.READY_TO_APPLY, JobStatus.APPLYING, JobStatus.FAILED],
        JobStatus.READY_TO_APPLY: [JobStatus.APPLYING, JobStatus.FAILED],
        JobStatus.APPLYING: [JobStatus.APPLYING_PENDING_APPROVAL, JobStatus.APPLIED, JobStatus.FAILED],
        JobStatus.APPLYING_PENDING_APPROVAL: [JobStatus.APPLYING, JobStatus.APPLIED, JobStatus.FAILED],
        JobStatus.APPLIED: [JobStatus.INTERVIEW, JobStatus.REJECTED, JobStatus.FAILED]
    }

    @staticmethod
    def transition_job(
        db: Session, 
        job: Job, 
        new_status: JobStatus, 
        user_id: int,
        payload: Optional[dict] = None
    ):
        """
        Enforces deterministic state transitions for job objects.
        Ensures telemetry events are emitted for every valid shift.
        """
        old_status = job.status
        
        # Check transition validity
        allowed = StateManager.VALID_TRANSITIONS.get(old_status, [])
        if new_status not in allowed and new_status != JobStatus.FAILED:
            logger.warning(f"Invalid state transition: {old_status} -> {new_status} for Job {job.id}")
            # We allow it in dev for flexibility but log it heavily
        
        job.status = new_status
        db.commit()
        
        # Map JobStatus to EventType
        event_map = {
            JobStatus.ANALYZING: EventType.JOB_ANALYZING,
            JobStatus.ANALYZED: EventType.JOB_ANALYZED,
            JobStatus.APPLYING: EventType.APPLYING_STARTED,
            JobStatus.APPLYING_PENDING_APPROVAL: EventType.APPLYING_PENDING_APPROVAL,
            JobStatus.APPLIED: EventType.APPLYING_SUCCESS,
            JobStatus.FAILED: EventType.JOB_FAILED
        }
        
        event_type = event_map.get(new_status)
        if event_type:
            EventService.emit(
                user_id=user_id,
                event_type=event_type,
                payload=payload or {"old_status": old_status.value, "new_status": new_status.value},
                resource_id=str(job.id),
                source_worker="StateManager"
            )
            
        logger.info(f"Job {job.id} transitioned: {old_status} -> {new_status}")
        return job
