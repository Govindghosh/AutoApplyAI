from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.team_governance import (
    ApprovalChainStatus,
    GovernanceApprovalChain,
    IncidentComment,
    IncidentStatus,
    IncidentThread,
    OperatorRole,
    TeamOperatorRole,
    WorkflowInterventionAudit,
    WorkflowLock,
    WorkflowOversightAssignment,
)
from app.models.workflow import ApplicationWorkflow


class TeamGovernanceService:
    ROLE_CAPABILITIES: dict[str, list[str]] = {
        OperatorRole.USER.value: [
            "manage_own_workflows",
            "request_replay",
            "resolve_own_escalation",
        ],
        OperatorRole.REVIEWER.value: [
            "review_governance_changes",
            "approve_policy_chain",
            "comment_incidents",
        ],
        OperatorRole.SUPPORT_OPERATOR.value: [
            "assist_workflow_recovery",
            "acquire_workflow_lock",
            "transfer_escalation",
            "comment_incidents",
        ],
        OperatorRole.ADMIN.value: [
            "manage_own_workflows",
            "platform_operational_control",
            "review_governance_changes",
            "approve_policy_chain",
            "assist_workflow_recovery",
            "acquire_workflow_lock",
            "transfer_escalation",
            "manage_operator_roles",
            "comment_incidents",
        ],
        OperatorRole.AUDITOR.value: [
            "read_governance_visibility",
            "view_audit_timeline",
        ],
    }

    @classmethod
    def build_dashboard(cls, db: Session, owner_user_id: int, actor_user_id: int | None = None) -> dict[str, Any]:
        actor_user_id = actor_user_id or owner_user_id
        cls.ensure_owner_role(db, owner_user_id)

        roles = db.query(TeamOperatorRole).filter(
            TeamOperatorRole.owner_user_id == owner_user_id,
            TeamOperatorRole.is_active.is_(True),
        ).all()
        assignments = db.query(WorkflowOversightAssignment).filter(
            WorkflowOversightAssignment.owner_user_id == owner_user_id
        ).order_by(WorkflowOversightAssignment.created_at.desc()).limit(12).all()
        locks = db.query(WorkflowLock).filter(
            WorkflowLock.owner_user_id == owner_user_id,
            WorkflowLock.released_at.is_(None),
        ).order_by(WorkflowLock.created_at.desc()).all()
        chains = db.query(GovernanceApprovalChain).filter(
            GovernanceApprovalChain.owner_user_id == owner_user_id
        ).order_by(GovernanceApprovalChain.created_at.desc()).limit(12).all()
        incidents = db.query(IncidentThread).filter(
            IncidentThread.owner_user_id == owner_user_id
        ).order_by(IncidentThread.created_at.desc()).limit(12).all()
        audit = db.query(WorkflowInterventionAudit).filter(
            WorkflowInterventionAudit.owner_user_id == owner_user_id
        ).order_by(WorkflowInterventionAudit.created_at.desc()).limit(20).all()

        return {
            "roles": [cls.serialize_role(role) for role in roles],
            "current_actor": {
                "user_id": actor_user_id,
                "roles": cls.roles_for_operator(db, owner_user_id, actor_user_id),
                "capabilities": cls.capabilities_for_operator(db, owner_user_id, actor_user_id),
            },
            "shared_workflow_oversight": {
                "assignments": [cls.serialize_assignment(item) for item in assignments],
                "active_locks": [cls.serialize_lock(item) for item in locks],
            },
            "approval_chains": [cls.serialize_chain(item) for item in chains],
            "incident_management": {
                "threads": [cls.serialize_incident(item) for item in incidents],
            },
            "multi_operator_audit_timeline": [cls.serialize_audit(item) for item in audit],
            "metrics": cls.metrics(assignments, locks, chains, audit),
            "guardrails": {
                "note": "Multi-operator features coordinate oversight and auditability; they do not change workflow node semantics.",
                "conflict_protection": [
                    "workflow locks",
                    "optimistic lock ownership",
                    "approval race prevention",
                    "audit timeline for every intervention",
                ],
            },
        }

    @classmethod
    def ensure_owner_role(cls, db: Session, owner_user_id: int) -> TeamOperatorRole:
        role = db.query(TeamOperatorRole).filter(
            TeamOperatorRole.owner_user_id == owner_user_id,
            TeamOperatorRole.operator_user_id == owner_user_id,
            TeamOperatorRole.role == OperatorRole.ADMIN,
            TeamOperatorRole.is_active.is_(True),
        ).first()
        if role:
            return role

        role = TeamOperatorRole(
            owner_user_id=owner_user_id,
            operator_user_id=owner_user_id,
            role=OperatorRole.ADMIN,
            metadata_json={"source": "default_owner_role"},
        )
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

    @classmethod
    def upsert_operator_role(
        cls,
        db: Session,
        owner_user_id: int,
        actor_user_id: int,
        operator_user_id: int,
        role: OperatorRole,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        cls.ensure_capability(db, owner_user_id, actor_user_id, "manage_operator_roles")
        existing = db.query(TeamOperatorRole).filter(
            TeamOperatorRole.owner_user_id == owner_user_id,
            TeamOperatorRole.operator_user_id == operator_user_id,
            TeamOperatorRole.role == role,
        ).first()
        if not existing:
            existing = TeamOperatorRole(
                owner_user_id=owner_user_id,
                operator_user_id=operator_user_id,
                role=role,
            )
            db.add(existing)
        existing.is_active = True
        existing.metadata_json = metadata or {}
        db.commit()
        db.refresh(existing)
        return cls.serialize_role(existing)

    @classmethod
    def assign_workflow(
        cls,
        db: Session,
        workflow: ApplicationWorkflow,
        actor_user_id: int,
        assigned_operator_id: int,
        assigned_role: OperatorRole,
        reason: str | None = None,
    ) -> dict[str, Any]:
        cls.ensure_capability(db, workflow.user_id, actor_user_id, "transfer_escalation")
        assignment = WorkflowOversightAssignment(
            workflow_id=workflow.id,
            owner_user_id=workflow.user_id,
            assigned_operator_id=assigned_operator_id,
            assigned_role=assigned_role,
            reason=reason,
        )
        db.add(assignment)
        cls.record_audit(
            db,
            owner_user_id=workflow.user_id,
            workflow_id=workflow.id,
            actor_user_id=actor_user_id,
            action="workflow_assigned",
            after_state={
                "assigned_operator_id": assigned_operator_id,
                "assigned_role": assigned_role.value if hasattr(assigned_role, "value") else str(assigned_role),
            },
            reason=reason,
            commit=False,
        )
        db.commit()
        db.refresh(assignment)
        return cls.serialize_assignment(assignment)

    @classmethod
    def acquire_lock(
        cls,
        db: Session,
        workflow: ApplicationWorkflow,
        actor_user_id: int,
        lock_scope: str = "workflow",
        ttl_minutes: int = 30,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        cls.ensure_capability(db, workflow.user_id, actor_user_id, "acquire_workflow_lock")
        active = cls.active_lock(db, workflow.id)
        if active and active.locked_by_user_id != actor_user_id:
            cls.record_audit(
                db,
                owner_user_id=workflow.user_id,
                workflow_id=workflow.id,
                actor_user_id=actor_user_id,
                action="workflow_lock_conflict",
                before_state=cls.serialize_lock(active),
                reason="Active workflow lock is owned by another operator.",
                commit=True,
            )
            raise HTTPException(status_code=409, detail={"message": "Workflow is locked by another operator", "lock": cls.serialize_lock(active)})

        if active:
            active.expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
            db.commit()
            db.refresh(active)
            return cls.serialize_lock(active)

        lock = WorkflowLock(
            workflow_id=workflow.id,
            owner_user_id=workflow.user_id,
            locked_by_user_id=actor_user_id,
            lock_scope=lock_scope,
            lock_token=str(uuid4()),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
            metadata_json=metadata or {},
        )
        db.add(lock)
        cls.record_audit(
            db,
            owner_user_id=workflow.user_id,
            workflow_id=workflow.id,
            actor_user_id=actor_user_id,
            action="workflow_lock_acquired",
            after_state={"lock_scope": lock_scope},
            commit=False,
        )
        db.commit()
        db.refresh(lock)
        return cls.serialize_lock(lock)

    @classmethod
    def release_lock(cls, db: Session, lock_id: int, actor_user_id: int) -> dict[str, Any]:
        lock = db.query(WorkflowLock).filter(WorkflowLock.id == lock_id).first()
        if not lock:
            raise HTTPException(status_code=404, detail="Workflow lock not found")
        cls.ensure_capability(db, lock.owner_user_id, actor_user_id, "acquire_workflow_lock")
        if lock.locked_by_user_id != actor_user_id and "platform_operational_control" not in cls.capabilities_for_operator(db, lock.owner_user_id, actor_user_id):
            raise HTTPException(status_code=403, detail="Only the lock owner or an admin can release this lock")
        lock.released_at = datetime.now(timezone.utc)
        cls.record_audit(
            db,
            owner_user_id=lock.owner_user_id,
            workflow_id=lock.workflow_id,
            actor_user_id=actor_user_id,
            action="workflow_lock_released",
            before_state=cls.serialize_lock(lock),
            commit=False,
        )
        db.commit()
        db.refresh(lock)
        return cls.serialize_lock(lock)

    @classmethod
    def assert_no_conflicting_lock(cls, db: Session, workflow: ApplicationWorkflow, actor_user_id: int) -> None:
        active = cls.active_lock(db, workflow.id)
        if active and active.locked_by_user_id != actor_user_id:
            cls.record_audit(
                db,
                owner_user_id=workflow.user_id,
                workflow_id=workflow.id,
                actor_user_id=actor_user_id,
                action="workflow_lock_conflict",
                before_state=cls.serialize_lock(active),
                reason="Active workflow lock is owned by another operator.",
                commit=True,
            )
            raise HTTPException(status_code=409, detail={"message": "Workflow is locked by another operator", "lock": cls.serialize_lock(active)})

    @classmethod
    def active_lock(cls, db: Session, workflow_id: int) -> WorkflowLock | None:
        now = datetime.now(timezone.utc)
        locks = db.query(WorkflowLock).filter(
            WorkflowLock.workflow_id == workflow_id,
            WorkflowLock.released_at.is_(None),
        ).order_by(WorkflowLock.created_at.desc()).all()
        for lock in locks:
            expires_at = cls._aware(lock.expires_at)
            if not expires_at or expires_at > now:
                return lock
            lock.released_at = now
        if locks:
            db.commit()
        return None

    @classmethod
    def create_approval_chain(
        cls,
        db: Session,
        owner_user_id: int,
        actor_user_id: int,
        resource_type: str,
        resource_id: str,
        action: str,
        required_roles: list[OperatorRole],
    ) -> dict[str, Any]:
        cls.ensure_capability(db, owner_user_id, actor_user_id, "review_governance_changes")
        chain = GovernanceApprovalChain(
            owner_user_id=owner_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            required_roles=[role.value if hasattr(role, "value") else str(role) for role in required_roles],
            approvals=[],
            created_by_user_id=actor_user_id,
        )
        db.add(chain)
        db.commit()
        db.refresh(chain)
        return cls.serialize_chain(chain)

    @classmethod
    def approve_chain(
        cls,
        db: Session,
        chain_id: int,
        actor_user_id: int,
        note: str | None = None,
    ) -> dict[str, Any]:
        chain = db.query(GovernanceApprovalChain).filter(GovernanceApprovalChain.id == chain_id).first()
        if not chain:
            raise HTTPException(status_code=404, detail="Approval chain not found")
        cls.ensure_capability(db, chain.owner_user_id, actor_user_id, "approve_policy_chain")
        before = cls.serialize_chain(chain)
        approvals = chain.approvals or []
        roles = cls.roles_for_operator(db, chain.owner_user_id, actor_user_id)
        approvals.append({
            "actor_user_id": actor_user_id,
            "roles": roles,
            "note": note,
            "approved_at": datetime.now(timezone.utc).isoformat(),
        })
        chain.approvals = approvals
        approved_roles = {role for approval in approvals for role in approval.get("roles", [])}
        if set(chain.required_roles or []).issubset(approved_roles):
            chain.status = ApprovalChainStatus.APPROVED
            chain.completed_at = datetime.now(timezone.utc)

        cls.record_audit(
            db,
            owner_user_id=chain.owner_user_id,
            workflow_id=None,
            actor_user_id=actor_user_id,
            action="approval_chain_approved",
            before_state=before,
            after_state=cls.serialize_chain(chain),
            reason=note,
            commit=False,
        )
        db.commit()
        db.refresh(chain)
        return cls.serialize_chain(chain)

    @classmethod
    def open_incident(
        cls,
        db: Session,
        owner_user_id: int,
        actor_user_id: int,
        title: str,
        workflow_id: int | None = None,
        severity: str = "medium",
        assigned_operator_id: int | None = None,
    ) -> dict[str, Any]:
        cls.ensure_capability(db, owner_user_id, actor_user_id, "comment_incidents")
        incident = IncidentThread(
            owner_user_id=owner_user_id,
            workflow_id=workflow_id,
            title=title,
            severity=severity,
            assigned_operator_id=assigned_operator_id,
            created_by_user_id=actor_user_id,
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        return cls.serialize_incident(incident)

    @classmethod
    def add_incident_comment(
        cls,
        db: Session,
        incident_id: int,
        actor_user_id: int,
        comment: str,
        annotation_type: str = "comment",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        incident = db.query(IncidentThread).filter(IncidentThread.id == incident_id).first()
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        cls.ensure_capability(db, incident.owner_user_id, actor_user_id, "comment_incidents")
        item = IncidentComment(
            incident_id=incident.id,
            actor_user_id=actor_user_id,
            comment=comment,
            annotation_type=annotation_type,
            metadata_json=metadata or {},
        )
        incident.status = IncidentStatus.IN_PROGRESS
        db.add(item)
        db.commit()
        db.refresh(item)
        return cls.serialize_comment(item)

    @classmethod
    def record_audit(
        cls,
        db: Session,
        owner_user_id: int,
        workflow_id: int | None,
        actor_user_id: int,
        action: str,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        reason: str | None = None,
        commit: bool = True,
    ) -> None:
        db.add(WorkflowInterventionAudit(
            owner_user_id=owner_user_id,
            workflow_id=workflow_id,
            actor_user_id=actor_user_id,
            action=action,
            before_state=before_state,
            after_state=after_state,
            reason=reason,
        ))
        if commit:
            db.commit()

    @classmethod
    def roles_for_operator(cls, db: Session, owner_user_id: int, actor_user_id: int) -> list[str]:
        cls.ensure_owner_role(db, owner_user_id)
        roles = db.query(TeamOperatorRole).filter(
            TeamOperatorRole.owner_user_id == owner_user_id,
            TeamOperatorRole.operator_user_id == actor_user_id,
            TeamOperatorRole.is_active.is_(True),
        ).all()
        return sorted({role.role.value if hasattr(role.role, "value") else str(role.role) for role in roles})

    @classmethod
    def capabilities_for_operator(cls, db: Session, owner_user_id: int, actor_user_id: int) -> list[str]:
        capabilities: set[str] = set()
        for role in cls.roles_for_operator(db, owner_user_id, actor_user_id):
            capabilities.update(cls.ROLE_CAPABILITIES.get(role, []))
        return sorted(capabilities)

    @classmethod
    def ensure_capability(cls, db: Session, owner_user_id: int, actor_user_id: int, capability: str) -> None:
        capabilities = cls.capabilities_for_operator(db, owner_user_id, actor_user_id)
        if capability not in capabilities and "platform_operational_control" not in capabilities:
            raise HTTPException(status_code=403, detail=f"Missing team governance capability: {capability}")

    @classmethod
    def metrics(
        cls,
        assignments: list[WorkflowOversightAssignment],
        locks: list[WorkflowLock],
        chains: list[GovernanceApprovalChain],
        audit: list[WorkflowInterventionAudit],
    ) -> dict[str, Any]:
        actions = Counter(item.action for item in audit)
        completed_chains = [chain for chain in chains if chain.completed_at and chain.created_at]
        latencies = [
            (cls._aware(chain.completed_at) - cls._aware(chain.created_at)).total_seconds()
            for chain in completed_chains
            if cls._aware(chain.completed_at) and cls._aware(chain.created_at)
        ]
        return {
            "multi_operator_conflict_rate": round(
                (actions["workflow_lock_conflict"] / max(len(audit), 1)) * 100,
                2,
            ) if audit else 0,
            "approval_chain_latency_seconds": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "shared_replay_success": actions["replay_requested"],
            "governance_audit_completeness": round((len(audit) / max(len(assignments) + len(locks) + len(chains), 1)) * 100, 2),
            "escalation_transfer_rate": len([item for item in assignments if item.status == "active"]),
        }

    @staticmethod
    def serialize_role(role: TeamOperatorRole) -> dict[str, Any]:
        return {
            "id": role.id,
            "owner_user_id": role.owner_user_id,
            "operator_user_id": role.operator_user_id,
            "role": role.role.value if hasattr(role.role, "value") else str(role.role),
            "capabilities": TeamGovernanceService.ROLE_CAPABILITIES.get(
                role.role.value if hasattr(role.role, "value") else str(role.role),
                [],
            ),
            "is_active": role.is_active,
            "metadata": role.metadata_json or {},
            "created_at": role.created_at.isoformat() if role.created_at else None,
        }

    @staticmethod
    def serialize_assignment(item: WorkflowOversightAssignment) -> dict[str, Any]:
        return {
            "id": item.id,
            "workflow_id": item.workflow_id,
            "assigned_operator_id": item.assigned_operator_id,
            "assigned_role": item.assigned_role.value if hasattr(item.assigned_role, "value") else str(item.assigned_role),
            "status": item.status,
            "reason": item.reason,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }

    @staticmethod
    def serialize_lock(lock: WorkflowLock) -> dict[str, Any]:
        return {
            "id": lock.id,
            "workflow_id": lock.workflow_id,
            "locked_by_user_id": lock.locked_by_user_id,
            "lock_scope": lock.lock_scope,
            "lock_token": lock.lock_token,
            "expires_at": lock.expires_at.isoformat() if lock.expires_at else None,
            "released_at": lock.released_at.isoformat() if lock.released_at else None,
            "metadata": lock.metadata_json or {},
            "created_at": lock.created_at.isoformat() if lock.created_at else None,
        }

    @staticmethod
    def serialize_chain(chain: GovernanceApprovalChain) -> dict[str, Any]:
        return {
            "id": chain.id,
            "resource_type": chain.resource_type,
            "resource_id": chain.resource_id,
            "action": chain.action,
            "required_roles": chain.required_roles or [],
            "approvals": chain.approvals or [],
            "status": chain.status.value if hasattr(chain.status, "value") else str(chain.status),
            "created_by_user_id": chain.created_by_user_id,
            "created_at": chain.created_at.isoformat() if chain.created_at else None,
            "completed_at": chain.completed_at.isoformat() if chain.completed_at else None,
        }

    @staticmethod
    def serialize_incident(incident: IncidentThread) -> dict[str, Any]:
        return {
            "id": incident.id,
            "workflow_id": incident.workflow_id,
            "title": incident.title,
            "severity": incident.severity,
            "status": incident.status.value if hasattr(incident.status, "value") else str(incident.status),
            "assigned_operator_id": incident.assigned_operator_id,
            "created_by_user_id": incident.created_by_user_id,
            "created_at": incident.created_at.isoformat() if incident.created_at else None,
        }

    @staticmethod
    def serialize_comment(comment: IncidentComment) -> dict[str, Any]:
        return {
            "id": comment.id,
            "incident_id": comment.incident_id,
            "actor_user_id": comment.actor_user_id,
            "comment": comment.comment,
            "annotation_type": comment.annotation_type,
            "metadata": comment.metadata_json or {},
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
        }

    @staticmethod
    def serialize_audit(audit: WorkflowInterventionAudit) -> dict[str, Any]:
        return {
            "id": audit.id,
            "workflow_id": audit.workflow_id,
            "actor_user_id": audit.actor_user_id,
            "action": audit.action,
            "before_state": audit.before_state,
            "after_state": audit.after_state,
            "reason": audit.reason,
            "created_at": audit.created_at.isoformat() if audit.created_at else None,
        }

    @staticmethod
    def _aware(value: datetime | None) -> datetime | None:
        if not value:
            return None
        if value.tzinfo:
            return value
        return value.replace(tzinfo=timezone.utc)
