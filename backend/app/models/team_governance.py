import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class OperatorRole(str, enum.Enum):
    USER = "USER"
    REVIEWER = "REVIEWER"
    SUPPORT_OPERATOR = "SUPPORT_OPERATOR"
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"


class ApprovalChainStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class IncidentStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class TeamOperatorRole(Base):
    __tablename__ = "team_operator_roles"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    operator_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    role = Column(Enum(OperatorRole), default=OperatorRole.USER, index=True)
    is_active = Column(Boolean, default=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkflowOversightAssignment(Base):
    __tablename__ = "workflow_oversight_assignments"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("application_workflows.id"), index=True, nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    assigned_operator_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    assigned_role = Column(Enum(OperatorRole), default=OperatorRole.SUPPORT_OPERATOR)
    status = Column(String, default="active", index=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkflowLock(Base):
    __tablename__ = "workflow_locks"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("application_workflows.id"), index=True, nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    locked_by_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    lock_scope = Column(String, default="workflow", index=True)
    lock_token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class GovernanceApprovalChain(Base):
    __tablename__ = "governance_approval_chains"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    resource_type = Column(String, index=True)
    resource_id = Column(String, index=True)
    action = Column(String, index=True)
    required_roles = Column(JSON)
    approvals = Column(JSON, nullable=True)
    status = Column(Enum(ApprovalChainStatus), default=ApprovalChainStatus.PENDING, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class IncidentThread(Base):
    __tablename__ = "incident_threads"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    workflow_id = Column(Integer, ForeignKey("application_workflows.id"), nullable=True, index=True)
    title = Column(String)
    severity = Column(String, default="medium", index=True)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.OPEN, index=True)
    assigned_operator_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class IncidentComment(Base):
    __tablename__ = "incident_comments"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incident_threads.id"), index=True, nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    comment = Column(Text)
    annotation_type = Column(String, default="comment", index=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WorkflowInterventionAudit(Base):
    __tablename__ = "workflow_intervention_audits"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    workflow_id = Column(Integer, ForeignKey("application_workflows.id"), nullable=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    action = Column(String, index=True)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
