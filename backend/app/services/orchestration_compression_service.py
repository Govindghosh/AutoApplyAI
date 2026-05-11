from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import log2
from typing import Any

from sqlalchemy.orm import Session

from app.automation.workflow_primitives import WorkflowPrimitiveRegistry
from app.models.event import SystemEvent
from app.models.job import JobStatus
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.services.escalation_service import EscalationCompressionEngine
from app.services.event_taxonomy_service import EventTaxonomyService
from app.services.recovery_service import RecoveryCompressionService


class CanonicalWorkflowState(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    ACTIVE = "ACTIVE"
    WAITING = "WAITING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class FailureDisposition(str, Enum):
    RECOVERABLE = "recoverable"
    HUMAN_REQUIRED = "human_required"
    TERMINAL = "terminal"


class OrchestrationCompressionService:
    """
    Central complexity dashboard for Phase 30.
    """

    STATE_HIERARCHY: dict[str, Any] = {
        CanonicalWorkflowState.NOT_STARTED.value: {
            "children": ["queued"],
            "description": "Work exists but deterministic execution has not begun.",
        },
        CanonicalWorkflowState.ACTIVE.value: {
            "children": ["running", "applying", "analyzing"],
            "description": "Automation or analysis is currently executing.",
        },
        CanonicalWorkflowState.WAITING.value: {
            "children": ["approval", "human_input", "external_wait"],
            "description": "Execution is intentionally paused behind a boundary.",
        },
        CanonicalWorkflowState.SUCCEEDED.value: {
            "children": ["completed", "applied", "interview"],
            "description": "The workflow or downstream job outcome succeeded.",
        },
        CanonicalWorkflowState.FAILED.value: {
            "children": [
                FailureDisposition.RECOVERABLE.value,
                FailureDisposition.HUMAN_REQUIRED.value,
                FailureDisposition.TERMINAL.value,
            ],
            "description": "Execution failed and must choose a compressed recovery path.",
        },
        CanonicalWorkflowState.SKIPPED.value: {
            "children": ["intentionally_skipped"],
            "description": "Work was bypassed without treating it as a failure.",
        },
    }

    WORKFLOW_STATUS_MAP = {
        WorkflowStatus.PENDING.value: (CanonicalWorkflowState.NOT_STARTED.value, "queued"),
        WorkflowStatus.RUNNING.value: (CanonicalWorkflowState.ACTIVE.value, "running"),
        WorkflowStatus.PAUSED_FOR_HUMAN.value: (CanonicalWorkflowState.WAITING.value, "human_input"),
        WorkflowStatus.COMPLETED.value: (CanonicalWorkflowState.SUCCEEDED.value, "completed"),
        WorkflowStatus.FAILED.value: (CanonicalWorkflowState.FAILED.value, FailureDisposition.RECOVERABLE.value),
        WorkflowStatus.SKIPPED.value: (CanonicalWorkflowState.SKIPPED.value, "intentionally_skipped"),
    }

    JOB_STATUS_MAP = {
        JobStatus.SCRAPED.value: (CanonicalWorkflowState.NOT_STARTED.value, "queued"),
        JobStatus.ANALYSIS_PENDING.value: (CanonicalWorkflowState.NOT_STARTED.value, "queued"),
        JobStatus.ANALYZING.value: (CanonicalWorkflowState.ACTIVE.value, "analyzing"),
        JobStatus.ANALYZED.value: (CanonicalWorkflowState.NOT_STARTED.value, "queued"),
        JobStatus.ANALYSIS_FAILED.value: (CanonicalWorkflowState.FAILED.value, FailureDisposition.RECOVERABLE.value),
        JobStatus.SHORTLISTED.value: (CanonicalWorkflowState.NOT_STARTED.value, "queued"),
        JobStatus.READY_TO_APPLY.value: (CanonicalWorkflowState.NOT_STARTED.value, "queued"),
        JobStatus.APPLYING.value: (CanonicalWorkflowState.ACTIVE.value, "applying"),
        JobStatus.APPLYING_PENDING_APPROVAL.value: (CanonicalWorkflowState.WAITING.value, "approval"),
        JobStatus.APPLIED.value: (CanonicalWorkflowState.SUCCEEDED.value, "applied"),
        JobStatus.FAILED.value: (CanonicalWorkflowState.FAILED.value, FailureDisposition.RECOVERABLE.value),
        JobStatus.INTERVIEW.value: (CanonicalWorkflowState.SUCCEEDED.value, "interview"),
        JobStatus.REJECTED.value: (CanonicalWorkflowState.SUCCEEDED.value, "completed"),
    }

    @classmethod
    def build(cls, db: Session, user_id: int) -> dict[str, Any]:
        workflows = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.user_id == user_id).all()
        steps = db.query(WorkflowStep).join(ApplicationWorkflow).filter(ApplicationWorkflow.user_id == user_id).all()
        events = db.query(SystemEvent).filter(SystemEvent.user_id == user_id).all()

        steps_by_workflow: dict[int, list[WorkflowStep]] = defaultdict(list)
        for step in steps:
            steps_by_workflow[step.workflow_id].append(step)

        canonical_states = [
            cls.workflow_state(workflow.status)["state"]
            for workflow in workflows
        ] + [
            cls.workflow_state(step.status)["state"]
            for step in steps
        ]

        branching = cls._branching_depth(workflows, steps_by_workflow)
        escalations = [step for step in steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN]
        replay_loop_steps = [step for step in steps if (step.attempts or 0) >= 3]
        step_names = [step.name for step in steps]
        state_counts = Counter(canonical_states)

        return {
            "primitive_registry": {
                "version": "1.0.0",
                "total_primitives": len(WorkflowPrimitiveRegistry.list()),
                "primitives": WorkflowPrimitiveRegistry.list(),
                "step_mapping": WorkflowPrimitiveRegistry.WORKFLOW_STEP_TO_PRIMITIVE,
            },
            "state_surface": {
                "hierarchy": cls.STATE_HIERARCHY,
                "workflow_status_map": cls.WORKFLOW_STATUS_MAP,
                "job_status_map": cls.JOB_STATUS_MAP,
                "active_state_counts": [
                    {"state": state, "count": count}
                    for state, count in state_counts.most_common()
                ],
                "unique_canonical_states": len(set(canonical_states)),
            },
            "event_taxonomy": EventTaxonomyService.summarize_events(events),
            "escalation_templates": EscalationCompressionEngine.catalog(),
            "recovery_paths": RecoveryCompressionService.summarize_paths(workflows, steps_by_workflow),
            "complexity_dashboard": {
                "unique_workflow_states": len(set(cls._status_value(workflow.status) for workflow in workflows)),
                "unique_step_states": len(set(cls._status_value(step.status) for step in steps)),
                "avg_workflow_branching": branching["avg_branching"],
                "max_workflow_branching": branching["max_branching"],
                "escalation_density": round((len(escalations) / max(len(workflows), 1)), 2),
                "replay_loop_rate": round((len(replay_loop_steps) / max(len(steps), 1)) * 100, 2),
                "state_transition_entropy": cls._entropy(state_counts),
                "event_volume_growth": cls._event_volume_growth(events),
                "primitive_reuse_ratio": WorkflowPrimitiveRegistry.reuse_ratio(step_names),
            },
            "guardrails": {
                "note": "Compression is metadata-first and advisory where ambiguity exists.",
                "determinism_preserved_by": [
                    "durable checkpoint status",
                    "primitive versioning",
                    "non-blocking event validation",
                    "human-gated escalation templates",
                    "replay safety validation",
                ],
                "over_compression_risks": [
                    "hidden operational nuance",
                    "ambiguous failure disposition",
                    "lossy telemetry rollups before retention window",
                ],
            },
        }

    @classmethod
    def workflow_state(cls, status: Any) -> dict[str, str]:
        status_value = cls._status_value(status)
        state, leaf = cls.WORKFLOW_STATUS_MAP.get(
            status_value,
            (CanonicalWorkflowState.FAILED.value, FailureDisposition.RECOVERABLE.value),
        )
        return {"state": state, "leaf": leaf}

    @classmethod
    def job_state(cls, status: Any) -> dict[str, str]:
        status_value = cls._status_value(status)
        state, leaf = cls.JOB_STATUS_MAP.get(
            status_value,
            (CanonicalWorkflowState.FAILED.value, FailureDisposition.RECOVERABLE.value),
        )
        return {"state": state, "leaf": leaf}

    @classmethod
    def failure_disposition(cls, error: str | None, attempts: int = 0) -> str:
        error_lower = (error or "").lower()
        if any(token in error_lower for token in ["captcha", "login", "auth", "approval", "manual"]):
            return FailureDisposition.HUMAN_REQUIRED.value
        if attempts >= 3 or any(token in error_lower for token in ["duplicate", "closed", "forbidden"]):
            return FailureDisposition.TERMINAL.value
        return FailureDisposition.RECOVERABLE.value

    @classmethod
    def _branching_depth(
        cls,
        workflows: list[ApplicationWorkflow],
        steps_by_workflow: dict[int, list[WorkflowStep]],
    ) -> dict[str, float]:
        depths = []
        for workflow in workflows:
            steps = steps_by_workflow.get(workflow.id, [])
            depth = 1
            depth += len([step for step in steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN])
            depth += len([step for step in steps if step.status == WorkflowStatus.FAILED])
            depth += len([step for step in steps if (step.attempts or 0) > 1])
            depths.append(depth)

        return {
            "avg_branching": round(sum(depths) / len(depths), 2) if depths else 0,
            "max_branching": max(depths) if depths else 0,
        }

    @staticmethod
    def _event_volume_growth(events: list[SystemEvent]) -> float:
        now = datetime.now(timezone.utc)
        recent_start = now - timedelta(days=7)
        baseline_start = now - timedelta(days=14)

        recent = len([
            event for event in events
            if OrchestrationCompressionService._aware(event.timestamp) >= recent_start
        ])
        baseline = len([
            event for event in events
            if baseline_start <= OrchestrationCompressionService._aware(event.timestamp) < recent_start
        ])

        if baseline == 0:
            return 100 if recent else 0
        return round(((recent - baseline) / baseline) * 100, 2)

    @staticmethod
    def _entropy(counts: Counter[str]) -> float:
        total = sum(counts.values())
        if not total:
            return 0
        entropy = 0.0
        for count in counts.values():
            probability = count / total
            entropy -= probability * log2(probability)
        return round(entropy, 3)

    @staticmethod
    def _status_value(status: Any) -> str:
        return status.value if hasattr(status, "value") else str(status)

    @staticmethod
    def _aware(value: datetime | None) -> datetime:
        if not value:
            return datetime.fromtimestamp(0, tz=timezone.utc)
        if value.tzinfo:
            return value
        return value.replace(tzinfo=timezone.utc)
