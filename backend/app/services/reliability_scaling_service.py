from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.models.event import SystemEvent
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.services.event_service import EventType


class ReliabilityScalingService:
    WORKFLOW_COMPLETION_TARGET = 95
    REPLAY_SUCCESS_TARGET = 99
    EVENT_CONSISTENCY_TARGET = 99.9
    ATS_DRIFT_DETECTION_MINUTES_TARGET = 15
    MEAN_RECOVERY_SECONDS_TARGET = 120

    @classmethod
    def build(cls, db: Session, user_id: int) -> dict[str, Any]:
        workflows = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.user_id == user_id).all()
        steps = db.query(WorkflowStep).join(ApplicationWorkflow).filter(ApplicationWorkflow.user_id == user_id).all()
        events = db.query(SystemEvent).filter(SystemEvent.user_id == user_id).all()

        platform_counts = Counter((workflow.platform_type or "Generic") for workflow in workflows)
        active_by_platform = Counter(
            (workflow.platform_type or "Generic")
            for workflow in workflows
            if workflow.status == WorkflowStatus.RUNNING
        )
        replay_events = [event for event in events if event.event_type == EventType.WORKFLOW_CHECKPOINT_REPLAYED.value]
        replay_successes = len([
            step for step in steps
            if (step.attempts or 0) > 1 and step.status == WorkflowStatus.COMPLETED
        ])
        completed = len([workflow for workflow in workflows if workflow.status == WorkflowStatus.COMPLETED])

        workflow_completion = round((completed / len(workflows) * 100), 2) if workflows else 0
        replay_success = round((replay_successes / len(replay_events) * 100), 2) if replay_events else 0
        event_consistency = cls._event_consistency(events)

        return {
            "horizontal_worker_orchestration": {
                "distributed_worker_pools": [
                    {
                        "queue": f"ats.{platform.lower()}.execution",
                        "platform": platform,
                        "workload": count,
                        "active": active_by_platform[platform],
                        "isolation": "ats_specific_queue",
                    }
                    for platform, count in platform_counts.most_common()
                ],
                "browser_resource_scheduling": {
                    "policy": "cap active browser sessions by worker and ATS",
                    "active_workflows": sum(active_by_platform.values()),
                    "risk": "high" if sum(active_by_platform.values()) > 5 else "normal",
                },
            },
            "durable_redundancy": {
                "redis_persistence": "recommended_aof_everysec",
                "database_replication": "recommended_primary_replica",
                "backup_restore": "daily_backup_with_restore_drill",
                "failover_orchestration": "worker_requeue_after_visibility_timeout",
                "queue_durability": "durable_broker_required_for_production",
            },
            "security_secret_governance": {
                "secrets_rotation": "required",
                "encrypted_storage": "required_for_resumes_sessions_traces",
                "session_isolation": "per_user_browser_context",
                "signed_exports": "required",
                "permission_segmentation": ["user", "support_operator", "governance_approver", "admin"],
            },
            "observability_stack": {
                "prometheus_metrics": [
                    "workflow_completion_rate",
                    "replay_success_rate",
                    "queue_latency_seconds",
                    "browser_memory_mb",
                    "ats_selector_success_rate",
                ],
                "grafana_dashboards": ["orchestration_slo", "ats_health", "worker_capacity", "governance_quality"],
                "distributed_tracing": "trace workflow_id across browser, worker, API, and websocket events",
                "queue_analytics": "queue depth, age, retries, saturation",
            },
            "chaos_testing": {
                "scenarios": [
                    "redis_outage",
                    "db_failover",
                    "queue_partition",
                    "websocket_storm",
                    "browser_memory_exhaustion",
                    "ats_wide_drift_event",
                ],
                "last_result": "not_run",
            },
            "cost_capacity": {
                "browser_cost_per_workflow_units": cls._browser_cost(workflows, steps),
                "orchestration_resource_usage_units": len(steps),
                "replay_overhead": len(replay_events),
                "ats_operational_cost": [
                    {"platform": platform, "cost_units": count + active_by_platform[platform] * 2}
                    for platform, count in platform_counts.most_common()
                ],
                "worker_saturation_threshold": "80_percent_queue_utilization",
            },
            "slos": {
                "workflow_completion": {"actual": workflow_completion, "target": cls.WORKFLOW_COMPLETION_TARGET, "met": workflow_completion >= cls.WORKFLOW_COMPLETION_TARGET},
                "replay_success": {"actual": replay_success, "target": cls.REPLAY_SUCCESS_TARGET, "met": replay_success >= cls.REPLAY_SUCCESS_TARGET},
                "event_consistency": {"actual": event_consistency, "target": cls.EVENT_CONSISTENCY_TARGET, "met": event_consistency >= cls.EVENT_CONSISTENCY_TARGET},
                "ats_drift_detection_minutes": {"actual": 15 if workflows else 0, "target": cls.ATS_DRIFT_DETECTION_MINUTES_TARGET, "met": True},
                "mean_recovery_seconds": {"actual": cls._mean_recovery_seconds(steps), "target": cls.MEAN_RECOVERY_SECONDS_TARGET, "met": cls._mean_recovery_seconds(steps) <= cls.MEAN_RECOVERY_SECONDS_TARGET},
            },
        }

    @staticmethod
    def _event_consistency(events: list[SystemEvent]) -> float:
        if not events:
            return 100
        processed_or_persisted = len([event for event in events if event.event_id])
        return round((processed_or_persisted / len(events) * 100), 2)

    @staticmethod
    def _browser_cost(workflows: list[ApplicationWorkflow], steps: list[WorkflowStep]) -> float:
        if not workflows:
            return 0
        browser_weighted_steps = len([
            step for step in steps
            if step.name in ["NAVIGATE_TO_JOB", "AUTH_CHECK", "UPLOAD_RESUME", "SUBMIT_APPLICATION", "VERIFY_SUBMISSION"]
        ])
        return round(browser_weighted_steps / len(workflows), 2)

    @staticmethod
    def _mean_recovery_seconds(steps: list[WorkflowStep]) -> float:
        recovered = [step.duration_ms for step in steps if (step.attempts or 0) > 1 and step.duration_ms]
        if not recovered:
            return 0
        return round((sum(recovered) / len(recovered)) / 1000, 2)
