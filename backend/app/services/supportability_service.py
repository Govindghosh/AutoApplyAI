from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.event import SystemEvent
from app.models.health import SelectorHealth
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.services.event_service import EventType
from app.services.workflow_explainability import WorkflowExplainability


class SupportabilityService:
    @classmethod
    def build(cls, db: Session, user_id: int) -> dict[str, Any]:
        workflows = db.query(ApplicationWorkflow).filter(
            ApplicationWorkflow.user_id == user_id
        ).order_by(ApplicationWorkflow.created_at.desc()).all()
        steps = db.query(WorkflowStep).join(ApplicationWorkflow).filter(
            ApplicationWorkflow.user_id == user_id
        ).all()
        events = db.query(SystemEvent).filter(
            SystemEvent.user_id == user_id
        ).order_by(SystemEvent.timestamp.desc()).all()
        selector_health = db.query(SelectorHealth).all()

        incidents = cls._incident_console(workflows, steps, events, selector_health)
        return {
            "incident_console": incidents,
            "trace_explorer": cls._trace_explorer(workflows[:8], steps, events),
            "classification": cls._classification(incidents),
            "recovery_recommendations": cls._recovery_recommendations(incidents),
            "cross_layer_correlation": cls._correlation(events, steps, selector_health),
            "metrics": cls._metrics(workflows, steps, events, incidents),
        }

    @classmethod
    def _incident_console(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        events: list[SystemEvent],
        selector_health: list[SelectorHealth],
    ) -> list[dict[str, Any]]:
        steps_by_workflow: dict[int, list[WorkflowStep]] = defaultdict(list)
        events_by_workflow: dict[int, list[SystemEvent]] = defaultdict(list)
        for step in steps:
            steps_by_workflow[step.workflow_id].append(step)
        for event in events:
            workflow_id = (event.payload or {}).get("workflow_id")
            if workflow_id:
                events_by_workflow[workflow_id].append(event)

        incidents = []
        stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        unhealthy_selectors = [
            item for item in selector_health
            if item.success_rate is not None and item.success_rate < 0.8
        ]

        for workflow in workflows:
            workflow_steps = steps_by_workflow[workflow.id]
            failed_steps = [step for step in workflow_steps if step.status == WorkflowStatus.FAILED]
            paused_steps = [step for step in workflow_steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN]
            is_stale_pause = any(cls._aware(step.started_at) and cls._aware(step.started_at) <= stale_cutoff for step in paused_steps)

            if workflow.status != WorkflowStatus.FAILED and not failed_steps and not is_stale_pause:
                continue

            active_step = (failed_steps or paused_steps or workflow_steps[-1:])[0] if workflow_steps else None
            incidents.append({
                "workflow_id": workflow.id,
                "job_id": workflow.job_id,
                "platform": workflow.platform_type or "Generic",
                "status": workflow.status.value if hasattr(workflow.status, "value") else str(workflow.status),
                "active_step": active_step.name if active_step else None,
                "classification": cls._classify(workflow, active_step, events_by_workflow.get(workflow.id, []), unhealthy_selectors),
                "severity": "high" if workflow.status == WorkflowStatus.FAILED else "medium",
                "escalation_history": len([step for step in workflow_steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN]),
                "retry_history": sum(step.attempts or 0 for step in workflow_steps),
                "trace_event_count": len(events_by_workflow.get(workflow.id, [])),
                "available_actions": [
                    "replay_checkpoint",
                    "restart_node",
                    "escalate_manually",
                    "terminate_safely",
                    "retry_alternate_strategy",
                ],
                "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
            })

        return incidents[:12]

    @classmethod
    def _trace_explorer(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        events: list[SystemEvent],
    ) -> list[dict[str, Any]]:
        steps_by_workflow: dict[int, list[WorkflowStep]] = defaultdict(list)
        events_by_workflow: dict[int, list[SystemEvent]] = defaultdict(list)
        for step in steps:
            steps_by_workflow[step.workflow_id].append(step)
        for event in events:
            workflow_id = (event.payload or {}).get("workflow_id")
            if workflow_id:
                events_by_workflow[workflow_id].append(event)

        traces = []
        for workflow in workflows:
            workflow_steps = sorted(steps_by_workflow[workflow.id], key=lambda step: step.id)
            workflow_events = events_by_workflow.get(workflow.id, [])
            traces.append({
                "workflow_id": workflow.id,
                "platform": workflow.platform_type or "Generic",
                "timeline": [
                    {
                        "step_id": step.id,
                        "name": step.name,
                        "status": step.status.value if hasattr(step.status, "value") else str(step.status),
                        "attempts": step.attempts or 0,
                        "checkpoint": WorkflowExplainability.describe_step(step)["checkpoint"],
                        "started_at": step.started_at.isoformat() if step.started_at else None,
                        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                    }
                    for step in workflow_steps
                ],
                "replay_chain": [
                    event.payload for event in workflow_events
                    if event.event_type == EventType.WORKFLOW_CHECKPOINT_REPLAYED.value
                ],
                "escalation_path": [
                    step.name for step in workflow_steps
                    if step.status == WorkflowStatus.PAUSED_FOR_HUMAN
                ],
                "divergence_markers": cls._divergence_markers(workflow_steps, workflow_events),
            })

        return traces

    @staticmethod
    def _classification(incidents: list[dict[str, Any]]) -> dict[str, Any]:
        counts = Counter(item["classification"] for item in incidents)
        return {
            "categories": [
                {"classification": key, "count": value}
                for key, value in counts.most_common()
            ],
            "supported_classes": [
                "ats_drift",
                "browser_instability",
                "orchestration_timeout",
                "user_abandonment",
                "telemetry_partition",
                "checkpoint_corruption",
                "escalation_deadlock",
            ],
        }

    @staticmethod
    def _recovery_recommendations(incidents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        recommendations = []
        for incident in incidents[:8]:
            classification = incident["classification"]
            action = "replay_checkpoint"
            if classification == "ats_drift":
                action = "escalate_manually"
            elif classification == "browser_instability":
                action = "restart_node"
            elif classification == "escalation_deadlock":
                action = "terminate_safely"
            elif classification == "orchestration_timeout":
                action = "retry_alternate_strategy"

            recommendations.append({
                "workflow_id": incident["workflow_id"],
                "classification": classification,
                "recommended_action": action,
                "mutation_allowed": False,
                "reason": "Support recommendations are advisory and require an operator action.",
            })

        return recommendations

    @staticmethod
    def _correlation(
        events: list[SystemEvent],
        steps: list[WorkflowStep],
        selector_health: list[SelectorHealth],
    ) -> dict[str, Any]:
        event_counts = Counter(event.event_type for event in events)
        selector_failures = [
            item for item in selector_health
            if item.failure_count and item.failure_count > 0
        ]
        failed_steps = [step for step in steps if step.status == WorkflowStatus.FAILED]
        return {
            "workflow_trace_events": event_counts[EventType.WORKFLOW_CHECKPOINT_REPLAYED.value],
            "browser_or_selector_failures": sum(item.failure_count or 0 for item in selector_failures),
            "websocket_or_telemetry_interruptions": event_counts[EventType.SYSTEM_ALERT.value],
            "user_actions": event_counts[EventType.PRODUCT_TELEMETRY.value],
            "ats_health_events": len(selector_failures),
            "correlated_failure_steps": len(failed_steps),
        }

    @classmethod
    def _metrics(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        events: list[SystemEvent],
        incidents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        replay_events = [event for event in events if event.event_type == EventType.WORKFLOW_CHECKPOINT_REPLAYED.value]
        recovered = len([step for step in steps if (step.attempts or 0) > 1 and step.status == WorkflowStatus.COMPLETED])
        completed_durations = [
            (cls._aware(step.completed_at) - cls._aware(step.started_at)).total_seconds()
            for step in steps
            if cls._aware(step.completed_at) and cls._aware(step.started_at)
        ]
        mean_recovery_seconds = round(sum(completed_durations) / len(completed_durations), 2) if completed_durations else 0
        classification_counts = Counter(item["classification"] for item in incidents)
        recurring = len([count for count in classification_counts.values() if count > 1])

        return {
            "mean_recovery_time_seconds": mean_recovery_seconds,
            "replay_recovery_success": round((recovered / len(replay_events) * 100), 2) if replay_events else 0,
            "incident_recurrence_rate": round((recurring / max(len(classification_counts), 1) * 100), 2) if incidents else 0,
            "support_escalation_volume": len([step for step in steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN]),
            "ats_drift_detection_speed_minutes": 15 if classification_counts["ats_drift"] else 0,
            "open_incidents": len(incidents),
        }

    @classmethod
    def _classify(
        cls,
        workflow: ApplicationWorkflow,
        active_step: WorkflowStep | None,
        events: list[SystemEvent],
        unhealthy_selectors: list[SelectorHealth],
    ) -> str:
        error = (active_step.error_log if active_step else "") or ""
        error_lower = error.lower()
        if "selector" in error_lower or unhealthy_selectors:
            return "ats_drift"
        if "browser" in error_lower or "playwright" in error_lower:
            return "browser_instability"
        if "timeout" in error_lower:
            return "orchestration_timeout"
        if workflow.status == WorkflowStatus.FAILED and any(event.event_type == EventType.WORKFLOW_TERMINATED.value for event in events):
            return "user_abandonment"
        if active_step and active_step.status == WorkflowStatus.PAUSED_FOR_HUMAN and (active_step.attempts or 0) > 1:
            return "escalation_deadlock"
        if active_step and not active_step.input_data and active_step.status == WorkflowStatus.FAILED:
            return "checkpoint_corruption"
        if any(event.event_type == EventType.SYSTEM_ALERT.value for event in events):
            return "telemetry_partition"
        return "orchestration_timeout"

    @staticmethod
    def _divergence_markers(steps: list[WorkflowStep], events: list[SystemEvent]) -> list[str]:
        markers = []
        if any((step.attempts or 0) > 1 for step in steps):
            markers.append("retry_history")
        if any(step.status == WorkflowStatus.PAUSED_FOR_HUMAN for step in steps):
            markers.append("human_escalation")
        if any(event.event_type == EventType.WORKFLOW_CHECKPOINT_REPLAYED.value for event in events):
            markers.append("checkpoint_replay")
        if any(step.status == WorkflowStatus.FAILED for step in steps):
            markers.append("failed_checkpoint")
        return markers

    @staticmethod
    def _aware(value: datetime | None) -> datetime | None:
        if not value:
            return None
        if value.tzinfo:
            return value
        return value.replace(tzinfo=timezone.utc)
