import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class RecommendationStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"


class OperationalRecommendation(Base):
    __tablename__ = "operational_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    source_signal = Column(String, index=True)
    recommendation_type = Column(String, index=True)
    title = Column(String)
    rationale = Column(Text)
    target_policy = Column(String)
    proposed_change = Column(JSON)
    rollback_plan = Column(JSON)
    explainability = Column(JSON)
    shadow_evaluation = Column(JSON)
    status = Column(Enum(RecommendationStatus), default=RecommendationStatus.PENDING_REVIEW, index=True)
    reviewer_id = Column(Integer, nullable=True, index=True)
    decision_note = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    implemented_at = Column(DateTime(timezone=True), nullable=True)
    rolled_back_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class GovernanceTimelineEntry(Base):
    __tablename__ = "governance_timeline_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    recommendation_id = Column(Integer, ForeignKey("operational_recommendations.id"), index=True)
    actor_user_id = Column(Integer, nullable=True, index=True)
    action = Column(String, index=True)
    reason = Column(Text, nullable=True)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    outcome_metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
