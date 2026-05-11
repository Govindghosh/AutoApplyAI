from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.ats_capability_service import ATSCapabilityService

router = APIRouter(prefix="/ats", tags=["ats-governance"])


@router.get("/capability-matrix")
async def get_ats_capability_matrix(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return ATSCapabilityService.build_dashboard(db, current_user.id)


@router.get("/risk-dashboard")
async def get_ats_risk_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    dashboard = ATSCapabilityService.build_dashboard(db, current_user.id)
    return {
        "operational_risk_dashboard": dashboard["operational_risk_dashboard"],
        "capability_based_policies": dashboard["capability_based_policies"],
        "guardrails": dashboard["guardrails"],
    }


@router.get("/policies")
async def get_ats_policies(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return {
        "policies": ATSCapabilityService.policy_catalog(),
        "user_id": current_user.id,
    }


@router.post("/{platform}/certify")
async def certify_ats_adapter(
    platform: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return ATSCapabilityService.certify_adapter(db, platform, current_user.id)
