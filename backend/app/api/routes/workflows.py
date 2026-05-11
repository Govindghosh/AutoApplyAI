from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.models.job import Job, JobStatus
from app.services.event_service import EventService, EventType
from app.services.personalization_service import OrchestrationPersonalizationService
from app.services.recovery_service import RecoveryCompressionService
from app.services.state_manager import StateManager
from app.services.team_governance_service import TeamGovernanceService
from app.services.workflow_explainability import WorkflowExplainability
from app.services.workflow_orchestrator import WorkflowOrchestrator

router = APIRouter(prefix="/workflows", tags=["workflows"])


class StepReportRequest(BaseModel):
    note: str | None = None


class TerminateWorkflowRequest(BaseModel):
    reason: str | None = None


def serialize_workflow_details(workflow: ApplicationWorkflow, steps: list[WorkflowStep], db: Session | None = None):
    profile = OrchestrationPersonalizationService.get_or_create_profile(db, workflow.user_id) if db else None
    summary = WorkflowExplainability.describe_workflow(workflow, steps)
    if profile:
        summary = OrchestrationPersonalizationService.compress_workflow_summary(summary, workflow, steps, profile)

    return {
        "workflow": {
            "id": workflow.id,
            "job_id": workflow.job_id,
            "status": workflow.status,
            "platform": workflow.platform_type,
            "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
            "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
            "summary": summary,
        },
        "personalization": OrchestrationPersonalizationService.effective_policy(profile) if profile else None,
        "steps": [
            {
                "id": step.id,
                "name": step.name,
                "status": step.status,
                "attempts": step.attempts,
                "error": step.error_log,
                "duration": step.duration_ms,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "input_data": step.input_data,
                "output_data": step.output_data,
                "explanation": (
                    OrchestrationPersonalizationService.compress_step_explanation(
                        WorkflowExplainability.describe_step(step),
                        step,
                        workflow,
                        profile,
                    )
                    if profile else WorkflowExplainability.describe_step(step)
                ),
            } for step in steps
        ],
    }


def get_owned_workflow(db: Session, workflow_id: int, user_id: int) -> ApplicationWorkflow:
    workflow = db.query(ApplicationWorkflow).filter(
        ApplicationWorkflow.id == workflow_id,
        ApplicationWorkflow.user_id == user_id
    ).first()

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return workflow


def get_workflow_steps(db: Session, workflow_id: int) -> list[WorkflowStep]:
    return db.query(WorkflowStep).filter(
        WorkflowStep.workflow_id == workflow_id
    ).order_by(WorkflowStep.id).all()


@router.get("/by-job/{job_id}")
async def get_workflow_by_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workflow = db.query(ApplicationWorkflow).filter(
        ApplicationWorkflow.job_id == job_id,
        ApplicationWorkflow.user_id == current_user.id
    ).order_by(ApplicationWorkflow.created_at.desc()).first()

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return serialize_workflow_details(workflow, get_workflow_steps(db, workflow.id), db)


@router.get("/{workflow_id}")
async def get_workflow_details(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workflow = get_owned_workflow(db, workflow_id, current_user.id)
    return serialize_workflow_details(workflow, get_workflow_steps(db, workflow.id), db)

@router.post("/{workflow_id}/steps/{step_id}/retry")
async def retry_workflow_step(
    workflow_id: int,
    step_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workflow = get_owned_workflow(db, workflow_id, current_user.id)
    TeamGovernanceService.assert_no_conflicting_lock(db, workflow, current_user.id)
    
    step = db.query(WorkflowStep).filter(
        WorkflowStep.id == step_id,
        WorkflowStep.workflow_id == workflow.id,
    ).first()
    if not step: raise HTTPException(status_code=404)
    if step.status == WorkflowStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Completed checkpoints are already durable and cannot be replayed directly")

    workflow_steps = get_workflow_steps(db, workflow.id)
    recovery = RecoveryCompressionService.recommend(workflow, step, workflow_steps).to_dict()
    profile = OrchestrationPersonalizationService.get_or_create_profile(db, current_user.id)
    recovery["personalized_guidance"] = OrchestrationPersonalizationService.personalize_recovery_guidance(
        workflow,
        step,
        recovery,
        profile,
    )
    EventService.emit(
        current_user.id,
        EventType.WORKFLOW_RECOVERY_RECOMMENDED,
        {
            "workflow_id": workflow.id,
            "step_id": step.id,
            "step_name": step.name,
            "action": recovery["action"],
            "confidence": recovery["confidence"],
            "safety_validated": recovery["safety_validated"],
        },
        resource_id=str(workflow.job_id),
    )
    if recovery["action"] in ["manual_escalation", "terminate_safely"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Checkpoint replay is not the shortest safe recovery path for this step.",
                "recovery": recovery,
            },
        )
    
    # Reset step for retry
    step.status = WorkflowStatus.PENDING
    step.error_log = None
    step.started_at = None
    step.completed_at = None
    step.duration_ms = None
    workflow.status = WorkflowStatus.RUNNING
    db.commit()

    EventService.emit(
        current_user.id,
        EventType.WORKFLOW_CHECKPOINT_REPLAYED,
        {"workflow_id": workflow.id, "step_id": step.id, "step_name": step.name},
        resource_id=str(workflow.job_id),
    )
    TeamGovernanceService.record_audit(
        db,
        owner_user_id=workflow.user_id,
        workflow_id=workflow.id,
        actor_user_id=current_user.id,
        action="replay_requested",
        after_state={"step_id": step.id, "step_name": step.name, "recovery": recovery},
        reason="retry_workflow_step",
        commit=True,
    )
    
    # Trigger background task again if needed
    # (The worker loop will pick up the first pending step)
    from app.workers.tasks import apply_to_job_task
    apply_to_job_task.delay(workflow.job_id, current_user.id)
    
    return {"status": "retrying"}


@router.post("/{workflow_id}/replay-last-checkpoint")
async def replay_last_checkpoint(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workflow = get_owned_workflow(db, workflow_id, current_user.id)
    TeamGovernanceService.assert_no_conflicting_lock(db, workflow, current_user.id)
    step = db.query(WorkflowStep).filter(
        WorkflowStep.workflow_id == workflow.id,
        WorkflowStep.status.in_([WorkflowStatus.FAILED, WorkflowStatus.PAUSED_FOR_HUMAN]),
    ).order_by(WorkflowStep.id.desc()).first()

    if not step:
        raise HTTPException(status_code=400, detail="No failed or paused checkpoint is available to replay")

    workflow_steps = get_workflow_steps(db, workflow.id)
    recovery = RecoveryCompressionService.recommend(workflow, step, workflow_steps).to_dict()
    profile = OrchestrationPersonalizationService.get_or_create_profile(db, current_user.id)
    recovery["personalized_guidance"] = OrchestrationPersonalizationService.personalize_recovery_guidance(
        workflow,
        step,
        recovery,
        profile,
    )
    EventService.emit(
        current_user.id,
        EventType.WORKFLOW_RECOVERY_RECOMMENDED,
        {
            "workflow_id": workflow.id,
            "step_id": step.id,
            "step_name": step.name,
            "action": recovery["action"],
            "confidence": recovery["confidence"],
            "safety_validated": recovery["safety_validated"],
        },
        resource_id=str(workflow.job_id),
    )
    if recovery["action"] in ["manual_escalation", "terminate_safely"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Last checkpoint requires manual intervention or safe termination.",
                "recovery": recovery,
            },
        )

    step.status = WorkflowStatus.PENDING
    step.error_log = None
    step.started_at = None
    step.completed_at = None
    step.duration_ms = None
    workflow.status = WorkflowStatus.RUNNING
    db.commit()

    EventService.emit(
        current_user.id,
        EventType.WORKFLOW_CHECKPOINT_REPLAYED,
        {"workflow_id": workflow.id, "step_id": step.id, "step_name": step.name},
        resource_id=str(workflow.job_id),
    )
    TeamGovernanceService.record_audit(
        db,
        owner_user_id=workflow.user_id,
        workflow_id=workflow.id,
        actor_user_id=current_user.id,
        action="replay_requested",
        after_state={"step_id": step.id, "step_name": step.name, "recovery": recovery},
        reason="replay_last_checkpoint",
        commit=True,
    )

    from app.workers.tasks import apply_to_job_task
    apply_to_job_task.delay(workflow.job_id, current_user.id)

    return {"status": "replaying", "step_id": step.id}


@router.post("/{workflow_id}/steps/{step_id}/report")
async def report_workflow_step(
    workflow_id: int,
    step_id: int,
    payload: StepReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workflow = get_owned_workflow(db, workflow_id, current_user.id)
    TeamGovernanceService.assert_no_conflicting_lock(db, workflow, current_user.id)
    step = db.query(WorkflowStep).filter(
        WorkflowStep.id == step_id,
        WorkflowStep.workflow_id == workflow.id,
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail="Workflow step not found")

    EventService.emit(
        current_user.id,
        EventType.WORKFLOW_NODE_REPORTED,
        {
            "workflow_id": workflow.id,
            "step_id": step.id,
            "step_name": step.name,
            "status": step.status.value if hasattr(step.status, "value") else str(step.status),
            "note": payload.note,
        },
        resource_id=str(workflow.job_id),
    )

    return {"status": "reported"}


@router.post("/{workflow_id}/terminate")
async def terminate_workflow(
    workflow_id: int,
    payload: TerminateWorkflowRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workflow = get_owned_workflow(db, workflow_id, current_user.id)
    TeamGovernanceService.assert_no_conflicting_lock(db, workflow, current_user.id)
    workflow.status = WorkflowStatus.FAILED

    active_steps = db.query(WorkflowStep).filter(
        WorkflowStep.workflow_id == workflow.id,
        WorkflowStep.status.in_([WorkflowStatus.PENDING, WorkflowStatus.RUNNING, WorkflowStatus.PAUSED_FOR_HUMAN]),
    ).all()
    active_step_names = [step.name for step in active_steps]
    for step in active_steps:
        if step.status in [WorkflowStatus.RUNNING, WorkflowStatus.PAUSED_FOR_HUMAN]:
            step.status = WorkflowStatus.FAILED
            step.error_log = "Workflow terminated by user."

    job = db.query(Job).filter(Job.id == workflow.job_id).first()
    if job:
        StateManager.transition_job(
            db,
            job,
            JobStatus.FAILED,
            current_user.id,
            payload={"workflow_id": workflow.id, "reason": "terminated_by_user"},
        )
    else:
        db.commit()

    EventService.emit(
        current_user.id,
        EventType.WORKFLOW_TERMINATED,
        {
            "workflow_id": workflow.id,
            "job_id": workflow.job_id,
            "reason": payload.reason if payload and payload.reason else "unspecified",
            "active_steps": active_step_names,
        },
        resource_id=str(workflow.job_id),
    )
    TeamGovernanceService.record_audit(
        db,
        owner_user_id=workflow.user_id,
        workflow_id=workflow.id,
        actor_user_id=current_user.id,
        action="workflow_terminated",
        after_state={"reason": payload.reason if payload and payload.reason else "unspecified"},
        reason=payload.reason if payload else None,
        commit=True,
    )

    return {"status": "terminated"}


@router.post("/{workflow_id}/steps/{step_id}/resolve")
async def resolve_escalation(
    workflow_id: int,
    step_id: int,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Resolve a human-intervention task and resume the workflow.
    """
    workflow = get_owned_workflow(db, workflow_id, current_user.id)
    TeamGovernanceService.assert_no_conflicting_lock(db, workflow, current_user.id)
    
    step = db.query(WorkflowStep).filter(
        WorkflowStep.id == step_id,
        WorkflowStep.workflow_id == workflow.id,
    ).first()
    if not step: raise HTTPException(status_code=404)
    
    WorkflowOrchestrator.complete_step(
        db,
        step.id,
        {"human_resolved": True, "data": payload},
    )
    workflow.status = WorkflowStatus.RUNNING
    db.commit()
    TeamGovernanceService.record_audit(
        db,
        owner_user_id=workflow.user_id,
        workflow_id=workflow.id,
        actor_user_id=current_user.id,
        action="escalation_resolved",
        after_state={"step_id": step.id, "step_name": step.name},
        reason="human_resolved",
        commit=True,
    )
    
    # Resume workflow execution
    from app.workers.tasks import apply_to_job_task
    apply_to_job_task.delay(workflow.job_id, current_user.id)
    
    return {"status": "resumed"}
