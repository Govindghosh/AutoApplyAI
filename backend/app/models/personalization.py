import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class OrchestrationTrustMode(str, enum.Enum):
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    AGGRESSIVE = "AGGRESSIVE"


class ExplainabilityLevel(str, enum.Enum):
    BASIC = "BASIC"
    TECHNICAL = "TECHNICAL"
    OPERATIONAL = "OPERATIONAL"


class RecoveryGuidanceMode(str, enum.Enum):
    BEGINNER = "BEGINNER"
    ADVANCED = "ADVANCED"


class OrchestrationTrustProfile(Base):
    __tablename__ = "orchestration_trust_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)

    trust_mode = Column(Enum(OrchestrationTrustMode), default=OrchestrationTrustMode.BALANCED, index=True)
    explainability_level = Column(Enum(ExplainabilityLevel), default=ExplainabilityLevel.TECHNICAL)
    recovery_guidance_mode = Column(Enum(RecoveryGuidanceMode), default=RecoveryGuidanceMode.BEGINNER)

    verbose_explainability = Column(Boolean, default=False)
    minimal_explainability = Column(Boolean, default=False)
    escalation_batching = Column(Boolean, default=True)
    grouped_approvals = Column(Boolean, default=True)
    interruption_sensitivity = Column(String, default="normal")
    replay_auto_suggestions = Column(Boolean, default=True)
    captcha_handling_preference = Column(String, default="pause_with_guidance")

    # This is a presentation/governance cap. It does not alter the deterministic executor.
    max_replay_suggestions_per_workflow = Column(Integer, default=2)
    preference_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TrustCalibrationEvent(Base):
    __tablename__ = "trust_calibration_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    workflow_id = Column(Integer, ForeignKey("application_workflows.id"), nullable=True, index=True)
    step_id = Column(Integer, ForeignKey("workflow_steps.id"), nullable=True, index=True)

    event_name = Column(String, index=True)
    profile_mode = Column(String, index=True)
    latency_ms = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)
    value = Column(String, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
