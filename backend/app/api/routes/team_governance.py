from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.team_governance import OperatorRole
from app.models.user import User
from app.models.workflow import ApplicationWorkflow
from app.services.team_governance_service import TeamGovernanceService

router = APIRouter(prefix="/team-governance", tags=["team-governance"])


class OperatorRoleRequest(BaseModel):
    operator_user_id: int
    role: OperatorRole
    metadata: dict[str, Any] | None = None


class WorkflowAssignmentRequest(BaseModel):
    assigned_operator_id: int
    assigned_role: OperatorRole = OperatorRole.SUPPORT_OPERATOR
    reason: str | None = None


class WorkflowLockRequest(BaseModel):
    lock_scope: str = "workflow"
    ttl_minutes: int = 30
    metadata: dict[str, Any] | None = None


class ApprovalChainRequest(BaseModel):
    resource_type: str
    resource_id: str
    action: str
    required_roles: list[OperatorRole]


class ApprovalRequest(BaseModel):
    note: str | None = None


class IncidentRequest(BaseModel):
    title: str
    workflow_id: int | None = None
    severity: str = "medium"
    assigned_operator_id: int | None = None


class IncidentCommentRequest(BaseModel):
    comment: str
    annotation_type: str = "comment"
    metadata: dict[str, Any] | None = None


@router.get("/dashboard")
async def get_team_governance_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return TeamGovernanceService.build_dashboard(db, current_user.id, current_user.id)


@router.get("/roles/capabilities")
async def get_role_capabilities(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return {
        "user_id": current_user.id,
        "roles": TeamGovernanceService.ROLE_CAPABILITIES,
    }


@router.post("/operators")
async def upsert_operator_role(
    request: OperatorRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return TeamGovernanceService.upsert_operator_role(
        db,
        owner_user_id=current_user.id,
        actor_user_id=current_user.id,
        operator_user_id=request.operator_user_id,
        role=request.role,
        metadata=request.metadata,
    )


@router.post("/workflows/{workflow_id}/assign")
async def assign_workflow(
    workflow_id: int,
    request: WorkflowAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    workflow = _owned_workflow(db, workflow_id, current_user.id)
    return TeamGovernanceService.assign_workflow(
        db,
        workflow,
        actor_user_id=current_user.id,
        assigned_operator_id=request.assigned_operator_id,
        assigned_role=request.assigned_role,
        reason=request.reason,
    )


@router.post("/workflows/{workflow_id}/locks")
async def acquire_workflow_lock(
    workflow_id: int,
    request: WorkflowLockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    workflow = _owned_workflow(db, workflow_id, current_user.id)
    return TeamGovernanceService.acquire_lock(
        db,
        workflow,
        actor_user_id=current_user.id,
        lock_scope=request.lock_scope,
        ttl_minutes=request.ttl_minutes,
        metadata=request.metadata,
    )


@router.delete("/workflows/{workflow_id}/locks/{lock_id}")
async def release_workflow_lock(
    workflow_id: int,
    lock_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    _owned_workflow(db, workflow_id, current_user.id)
    return TeamGovernanceService.release_lock(db, lock_id, current_user.id)


@router.post("/approval-chains")
async def create_approval_chain(
    request: ApprovalChainRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return TeamGovernanceService.create_approval_chain(
        db,
        owner_user_id=current_user.id,
        actor_user_id=current_user.id,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        action=request.action,
        required_roles=request.required_roles,
    )


@router.post("/approval-chains/{chain_id}/approve")
async def approve_chain(
    chain_id: int,
    request: ApprovalRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return TeamGovernanceService.approve_chain(
        db,
        chain_id=chain_id,
        actor_user_id=current_user.id,
        note=request.note if request else None,
    )


@router.post("/incidents")
async def open_incident(
    request: IncidentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return TeamGovernanceService.open_incident(
        db,
        owner_user_id=current_user.id,
        actor_user_id=current_user.id,
        title=request.title,
        workflow_id=request.workflow_id,
        severity=request.severity,
        assigned_operator_id=request.assigned_operator_id,
    )


@router.post("/incidents/{incident_id}/comments")
async def add_incident_comment(
    incident_id: int,
    request: IncidentCommentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return TeamGovernanceService.add_incident_comment(
        db,
        incident_id=incident_id,
        actor_user_id=current_user.id,
        comment=request.comment,
        annotation_type=request.annotation_type,
        metadata=request.metadata,
    )


def _owned_workflow(db: Session, workflow_id: int, user_id: int) -> ApplicationWorkflow:
    workflow = db.query(ApplicationWorkflow).filter(
        ApplicationWorkflow.id == workflow_id,
        ApplicationWorkflow.user_id == user_id,
    ).first()
    if not workflow:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow
