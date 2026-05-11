import enum

from sqlalchemy import Column, DateTime, Enum, Float, Integer, JSON, String
from sqlalchemy.sql import func

from app.core.database import Base


class ATSAdapterStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    SANDBOX = "SANDBOX"
    CERTIFIED = "CERTIFIED"
    DISABLED = "DISABLED"


class ATSCertificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class ATSCapabilityMatrix(Base):
    __tablename__ = "ats_capability_matrix"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, unique=True, index=True, nullable=False)
    adapter_name = Column(String, nullable=True)
    adapter_status = Column(Enum(ATSAdapterStatus), default=ATSAdapterStatus.PLANNED, index=True)

    autofill_stability = Column(Float, default=0.0)
    replay_safety = Column(Float, default=0.0)
    drift_frequency = Column(Float, default=0.0)
    escalation_rate = Column(Float, default=0.0)
    submission_confidence = Column(Float, default=0.0)
    reliability_score = Column(Float, default=0.0)
    operational_risk = Column(String, default="unknown", index=True)

    policy = Column(JSON, nullable=True)
    capability_notes = Column(JSON, nullable=True)
    last_scored_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ATSCertificationRun(Base):
    __tablename__ = "ats_certification_runs"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, index=True, nullable=False)
    adapter_name = Column(String, nullable=True)
    status = Column(Enum(ATSCertificationStatus), default=ATSCertificationStatus.PENDING, index=True)
    score = Column(Float, default=0.0)
    checks = Column(JSON, nullable=True)
    report = Column(JSON, nullable=True)
    certified_by_user_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
