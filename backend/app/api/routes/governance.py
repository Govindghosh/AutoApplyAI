from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.governance_service import GovernanceService

router = APIRouter(prefix="/governance", tags=["governance"])


class GovernanceDecisionRequest(BaseModel):
    note: str | None = None


@router.get("/review-queue")
async def get_review_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return GovernanceService.build(db, current_user.id)


@router.post("/recommendations/{recommendation_id}/approve")
async def approve_recommendation(
    recommendation_id: int,
    payload: GovernanceDecisionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return GovernanceService.approve(db, recommendation_id, current_user.id, payload.note if payload else None)


@router.post("/recommendations/{recommendation_id}/reject")
async def reject_recommendation(
    recommendation_id: int,
    payload: GovernanceDecisionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return GovernanceService.reject(db, recommendation_id, current_user.id, payload.note if payload else None)


@router.post("/recommendations/{recommendation_id}/rollback")
async def rollback_recommendation(
    recommendation_id: int,
    payload: GovernanceDecisionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return GovernanceService.rollback(db, recommendation_id, current_user.id, payload.note if payload else None)
