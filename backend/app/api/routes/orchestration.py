from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.personalization import ExplainabilityLevel, OrchestrationTrustMode, RecoveryGuidanceMode
from app.models.user import User
from app.services.personalization_service import OrchestrationPersonalizationService

router = APIRouter(prefix="/orchestration", tags=["orchestration-personalization"])


class TrustProfileUpdateRequest(BaseModel):
    trust_mode: OrchestrationTrustMode | None = None
    explainability_level: ExplainabilityLevel | None = None
    recovery_guidance_mode: RecoveryGuidanceMode | None = None
    verbose_explainability: bool | None = None
    minimal_explainability: bool | None = None
    escalation_batching: bool | None = None
    grouped_approvals: bool | None = None
    interruption_sensitivity: str | None = None
    replay_auto_suggestions: bool | None = None
    captcha_handling_preference: str | None = None
    max_replay_suggestions_per_workflow: int | None = None
    preference_metadata: dict[str, Any] | None = None


class TrustCalibrationEventRequest(BaseModel):
    event_name: str
    workflow_id: int | None = None
    step_id: int | None = None
    latency_ms: int | None = None
    confidence: float | None = None
    value: str | None = None
    metadata: dict[str, Any] | None = None
    note: str | None = None


@router.get("/trust-profile")
async def get_trust_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    profile = OrchestrationPersonalizationService.get_or_create_profile(db, current_user.id)
    return {
        "profile": OrchestrationPersonalizationService.serialize_profile(profile),
        "effective_policy": OrchestrationPersonalizationService.effective_policy(profile),
    }


@router.patch("/trust-profile")
async def update_trust_profile(
    request: TrustProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    profile = OrchestrationPersonalizationService.update_profile(
        db,
        current_user.id,
        request.model_dump(exclude_unset=True),
    )
    return {
        "profile": OrchestrationPersonalizationService.serialize_profile(profile),
        "effective_policy": OrchestrationPersonalizationService.effective_policy(profile),
    }


@router.get("/trust-calibration/analytics")
async def get_trust_calibration_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return OrchestrationPersonalizationService.build_dashboard(db, current_user.id)


@router.post("/trust-calibration/events")
async def record_trust_calibration_event(
    request: TrustCalibrationEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return OrchestrationPersonalizationService.record_calibration_event(
        db,
        user_id=current_user.id,
        event_name=request.event_name,
        workflow_id=request.workflow_id,
        step_id=request.step_id,
        latency_ms=request.latency_ms,
        confidence=request.confidence,
        value=request.value,
        metadata=request.metadata,
        note=request.note,
    )
