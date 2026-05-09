from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.workflow import ApplicationWorkflow, WorkflowStep
from app.models.event import SystemEvent
from app.services.event_service import EventService, EventType
from app.services.workflow_explainability import WorkflowExplainability

router = APIRouter(prefix="/transparency", tags=["transparency"])


class ProductEventRequest(BaseModel):
    event_type: str
    payload: dict[str, Any] = {}
    resource_id: str | None = None


@router.get("/trace/{workflow_id}")
async def get_workflow_trace(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export a high-fidelity operational trace for debugging and transparency.
    """
    workflow = db.query(ApplicationWorkflow).filter(
        ApplicationWorkflow.id == workflow_id,
        ApplicationWorkflow.user_id == current_user.id
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    steps = db.query(WorkflowStep).filter(
        WorkflowStep.workflow_id == workflow.id
    ).order_by(WorkflowStep.id.asc()).all()

    # Get all events related to this specific workflow/job
    events = db.query(SystemEvent).filter(
        SystemEvent.user_id == current_user.id,
        SystemEvent.resource_id == str(workflow.job_id)
    ).order_by(SystemEvent.timestamp.asc()).all()

    EventService.emit(
        current_user.id,
        EventType.WORKFLOW_TRACE_EXPORTED,
        {"workflow_id": workflow.id, "job_id": workflow.job_id},
        resource_id=str(workflow.job_id),
    )
    
    return {
        "workflow": {
            "id": workflow.id,
            "job_id": workflow.job_id,
            "status": workflow.status,
            "platform": workflow.platform_type,
            "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
            "summary": WorkflowExplainability.describe_workflow(workflow, steps),
        },
        "steps": [
            {
                "id": step.id,
                "name": step.name,
                "status": step.status,
                "attempts": step.attempts,
                "error": step.error_log,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "duration": step.duration_ms,
                "input_data": step.input_data,
                "output_data": step.output_data,
                "explanation": WorkflowExplainability.describe_step(step),
            } for step in steps
        ],
        "timeline": [
            {
                "event_id": e.event_id,
                "type": e.event_type,
                "payload": e.payload,
                "timestamp": e.timestamp.isoformat()
            } for e in events
        ]
    }


@router.post("/product-events")
async def record_product_event(
    request: ProductEventRequest,
    current_user: User = Depends(get_current_user),
):
    event_map = {
        "onboarding_completed": EventType.ONBOARDING_COMPLETED,
    }
    event_type = event_map.get(request.event_type, EventType.PRODUCT_TELEMETRY)

    EventService.emit(
        current_user.id,
        event_type,
        {
            "event_type": request.event_type,
            **request.payload,
        },
        resource_id=request.resource_id,
    )

    return {"status": "recorded"}
