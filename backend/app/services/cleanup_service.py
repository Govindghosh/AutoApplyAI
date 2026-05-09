from sqlalchemy.orm import Session
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.core.database import SessionLocal
from datetime import datetime, timedelta, timezone
from app.core.logging import logger

class CleanupService:
    """
    Manages the lifecycle of 'paused' or 'stale' orchestration workflows.
    Prevents the accumulation of dead states and ensures system hygiene.
    """
    
    @staticmethod
    def cleanup_stale_interventions(timeout_hours: int = 24):
        db = SessionLocal()
        try:
            threshold = datetime.now(timezone.utc) - timedelta(hours=timeout_hours)
            
            # Find steps paused for human that haven't been touched in X hours
            stale_steps = db.query(WorkflowStep).filter(
                WorkflowStep.status == WorkflowStatus.PAUSED_FOR_HUMAN,
                WorkflowStep.started_at < threshold
            ).all()
            
            for step in stale_steps:
                logger.warning(f"Orchestration TIMEOUT for Step {step.id} (Workflow {step.workflow_id}). Marking as FAILED.")
                step.status = WorkflowStatus.FAILED
                step.error_log = "Human intervention timed out."
                
                # Update parent workflow
                workflow = db.query(ApplicationWorkflow).filter(
                    ApplicationWorkflow.id == step.workflow_id
                ).first()
                if workflow:
                    workflow.status = WorkflowStatus.FAILED
            
            db.commit()
            if stale_steps:
                logger.info(f"Cleaned up {len(stale_steps)} stale human interventions.")
        finally:
            db.close()
