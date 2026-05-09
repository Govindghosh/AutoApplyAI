from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.models.event import SystemEvent
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.services.event_service import EventType


class BehavioralMetricsService:
    @staticmethod
    def build(db: Session, user_id: int, total_workflows: int, stale_interventions: int) -> dict[str, Any]:
        workflow_steps = db.query(WorkflowStep).join(ApplicationWorkflow).filter(
            ApplicationWorkflow.user_id == user_id
        ).all()

        workflow_events = db.query(SystemEvent).filter(
            SystemEvent.user_id == user_id,
            SystemEvent.event_type.in_([
                EventType.WORKFLOW_CHECKPOINT_REPLAYED.value,
                EventType.WORKFLOW_NODE_REPORTED.value,
                EventType.WORKFLOW_TERMINATED.value,
                EventType.WORKFLOW_TRACE_EXPORTED.value,
            ]),
        ).all()

        product_events = db.query(SystemEvent).filter(
            SystemEvent.user_id == user_id,
            SystemEvent.event_type == EventType.PRODUCT_TELEMETRY.value,
        ).all()

        replay_events = [
            event for event in workflow_events
            if event.event_type == EventType.WORKFLOW_CHECKPOINT_REPLAYED.value
        ]
        report_events = [
            event for event in workflow_events
            if event.event_type == EventType.WORKFLOW_NODE_REPORTED.value
        ]
        termination_events = [
            event for event in workflow_events
            if event.event_type == EventType.WORKFLOW_TERMINATED.value
        ]

        step_by_id = {step.id: step for step in workflow_steps}
        replay_successes = 0
        replay_loops = 0
        replay_outcomes_by_step: Counter[str] = Counter()

        for event in replay_events:
            payload = event.payload or {}
            step = step_by_id.get(payload.get("step_id"))
            step_name = payload.get("step_name") or (step.name if step else "unknown")

            if step and step.status == WorkflowStatus.COMPLETED:
                replay_successes += 1
                replay_outcomes_by_step[f"{step_name}:success"] += 1
            elif step and step.status in [WorkflowStatus.FAILED, WorkflowStatus.PAUSED_FOR_HUMAN]:
                replay_loops += 1
                replay_outcomes_by_step[f"{step_name}:loop"] += 1
            else:
                replay_outcomes_by_step[f"{step_name}:pending"] += 1

        replay_count = len(replay_events)
        replay_success_rate = (replay_successes / replay_count * 100) if replay_count else 0

        human_resolved = 0
        human_pending = 0
        human_failed = 0
        for step in workflow_steps:
            output = step.output_data or {}
            if output.get("human_resolved") or output.get("approved_by_user"):
                human_resolved += 1
            elif step.status == WorkflowStatus.PAUSED_FOR_HUMAN:
                human_pending += 1
            elif step.status == WorkflowStatus.FAILED and step.error_log and "terminated by user" in step.error_log.lower():
                human_failed += 1

        escalation_total = human_resolved + human_pending + human_failed
        human_escalation_success_rate = (
            human_resolved / escalation_total * 100
        ) if escalation_total else 0

        repeated_retries = len([step for step in workflow_steps if step.attempts and step.attempts > 1])
        confusion_signal_count = (
            len(report_events)
            + repeated_retries
            + replay_loops
            + len(termination_events)
            + stale_interventions
        )
        intervention_confusion_rate = (
            confusion_signal_count / total_workflows * 100
        ) if total_workflows else 0

        supervisor_opens = BehavioralMetricsService._count_product_event(
            product_events,
            "workflow_supervisor_opened",
        )
        recovery_hint_actions = BehavioralMetricsService._count_product_event(
            product_events,
            "recovery_hint_actioned",
        )
        explanation_to_recovery_rate = (
            recovery_hint_actions / supervisor_opens * 100
        ) if supervisor_opens else 0

        termination_reasons: Counter[str] = Counter()
        terminations_by_step: Counter[str] = Counter()
        for event in termination_events:
            payload = event.payload or {}
            termination_reasons[payload.get("reason") or "unspecified"] += 1
            for step_name in payload.get("active_steps") or ["unknown"]:
                terminations_by_step[step_name] += 1

        trust_denominator = len(replay_events) + len(termination_events)
        trust_retention_rate = (
            len(replay_events) / trust_denominator * 100
        ) if trust_denominator else 0

        return {
            "intervention_confusion_rate": round(intervention_confusion_rate, 2),
            "confusion_signal_count": confusion_signal_count,
            "explainability": {
                "supervisor_opens": supervisor_opens,
                "recovery_hint_actions": recovery_hint_actions,
                "explanation_to_recovery_rate": round(explanation_to_recovery_rate, 2),
            },
            "human_escalation": {
                "resolved": human_resolved,
                "pending": human_pending,
                "failed": human_failed,
                "success_rate": round(human_escalation_success_rate, 2),
            },
            "replay": {
                "attempts": replay_count,
                "successes": replay_successes,
                "loops": replay_loops,
                "success_rate": round(replay_success_rate, 2),
                "outcomes_by_step": BehavioralMetricsService._counter_items(
                    replay_outcomes_by_step,
                    "outcome",
                ),
            },
            "termination": {
                "count": len(termination_events),
                "reasons": BehavioralMetricsService._counter_items(termination_reasons, "reason"),
                "by_step": BehavioralMetricsService._counter_items(terminations_by_step, "step_name"),
            },
            "trust_retention": {
                "continuation_actions": len(replay_events),
                "termination_actions": len(termination_events),
                "retention_rate": round(trust_retention_rate, 2),
            },
        }

    @staticmethod
    def _count_product_event(events: list[SystemEvent], event_type: str) -> int:
        return len([
            event for event in events
            if (event.payload or {}).get("event_type") == event_type
        ])

    @staticmethod
    def _counter_items(counter: Counter[str], key_name: str) -> list[dict[str, Any]]:
        return [
            {key_name: key, "count": count}
            for key, count in counter.most_common(5)
        ]
