from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models.event import SystemEvent
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.services.event_service import EventType


class PatternAnalysisService:
    DIRECTIONAL_SAMPLE_SIZE = 5
    STABLE_SAMPLE_SIZE = 20

    @classmethod
    def build(cls, db: Session, user_id: int) -> dict[str, Any]:
        workflows = db.query(ApplicationWorkflow).filter(
            ApplicationWorkflow.user_id == user_id
        ).all()
        steps = db.query(WorkflowStep).join(ApplicationWorkflow).filter(
            ApplicationWorkflow.user_id == user_id
        ).all()
        events = db.query(SystemEvent).filter(
            SystemEvent.user_id == user_id
        ).all()

        workflow_by_id = {workflow.id: workflow for workflow in workflows}
        replay_events = cls._events(events, EventType.WORKFLOW_CHECKPOINT_REPLAYED)
        report_events = cls._events(events, EventType.WORKFLOW_NODE_REPORTED)
        termination_events = cls._events(events, EventType.WORKFLOW_TERMINATED)
        product_events = cls._events(events, EventType.PRODUCT_TELEMETRY)

        node_patterns = cls._node_patterns(steps, replay_events, report_events, termination_events)
        ats_patterns = cls._ats_patterns(workflows, steps, replay_events, report_events, termination_events)
        explanation_patterns = cls._explanation_patterns(product_events, steps)
        intervention_fatigue = cls._intervention_fatigue(workflows, steps)
        trust_decay = cls._trust_decay(workflows, steps, termination_events)

        return {
            "analysis_guardrails": {
                "directional_sample_size": cls.DIRECTIONAL_SAMPLE_SIZE,
                "stable_sample_size": cls.STABLE_SAMPLE_SIZE,
                "note": (
                    "Phase 25 analytics are observational. Low-sample patterns should guide "
                    "review, not automatic policy changes."
                ),
            },
            "node_patterns": node_patterns,
            "explanation_patterns": explanation_patterns,
            "ats_friction": ats_patterns,
            "intervention_fatigue": intervention_fatigue,
            "trust_decay": trust_decay,
            "summary": cls._summary(node_patterns, ats_patterns, intervention_fatigue, trust_decay),
            "sample": {
                "workflows": len(workflows),
                "steps": len(steps),
                "events": len(events),
                "confidence": cls._confidence(len(workflows)),
            },
        }

    @classmethod
    def _node_patterns(
        cls,
        steps: list[WorkflowStep],
        replay_events: list[SystemEvent],
        report_events: list[SystemEvent],
        termination_events: list[SystemEvent],
    ) -> list[dict[str, Any]]:
        node_counts: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "observations": 0,
            "completed": 0,
            "failed": 0,
            "paused": 0,
            "human_interventions": 0,
            "repeated_retries": 0,
            "attempts": 0,
            "reports": 0,
            "replays": 0,
            "terminations": 0,
        })

        for step in steps:
            counts = node_counts[step.name]
            counts["observations"] += 1
            counts["attempts"] += step.attempts or 0

            if step.status == WorkflowStatus.COMPLETED:
                counts["completed"] += 1
            elif step.status == WorkflowStatus.FAILED:
                counts["failed"] += 1
            elif step.status == WorkflowStatus.PAUSED_FOR_HUMAN:
                counts["paused"] += 1

            output = step.output_data or {}
            if (
                step.status == WorkflowStatus.PAUSED_FOR_HUMAN
                or output.get("human_resolved")
                or output.get("approved_by_user")
            ):
                counts["human_interventions"] += 1

            if step.attempts and step.attempts > 1:
                counts["repeated_retries"] += 1

        for event in report_events:
            step_name = (event.payload or {}).get("step_name", "unknown")
            node_counts[step_name]["reports"] += 1

        for event in replay_events:
            step_name = (event.payload or {}).get("step_name", "unknown")
            node_counts[step_name]["replays"] += 1

        for event in termination_events:
            for step_name in (event.payload or {}).get("active_steps") or ["unknown"]:
                node_counts[step_name]["terminations"] += 1

        patterns = []
        for step_name, counts in node_counts.items():
            observations = counts["observations"]
            replay_rate = cls._rate(counts["replays"], observations)
            termination_rate = cls._rate(counts["terminations"], observations)
            report_rate = cls._rate(counts["reports"], observations)
            retry_rate = cls._rate(counts["repeated_retries"], observations)
            escalation_rate = cls._rate(counts["human_interventions"], observations)
            friction_score = min(
                100,
                round(
                    replay_rate * 0.25
                    + termination_rate * 0.3
                    + report_rate * 0.25
                    + retry_rate * 0.1
                    + escalation_rate * 0.1,
                    2,
                ),
            )

            patterns.append({
                "step_name": step_name,
                "observations": observations,
                "confidence": cls._confidence(observations),
                "friction_score": friction_score,
                "replay_rate": replay_rate,
                "termination_rate": termination_rate,
                "report_rate": report_rate,
                "retry_rate": retry_rate,
                "escalation_rate": escalation_rate,
                "counts": counts,
                "recommended_review": cls._node_recommendation(counts, observations),
            })

        return sorted(
            patterns,
            key=lambda item: (item["confidence"] == "insufficient", -item["friction_score"]),
        )[:8]

    @classmethod
    def _explanation_patterns(
        cls,
        product_events: list[SystemEvent],
        steps: list[WorkflowStep],
    ) -> list[dict[str, Any]]:
        opens_by_step: Counter[str] = Counter()
        hint_actions_by_step: Counter[str] = Counter()

        for event in product_events:
            payload = event.payload or {}
            event_type = payload.get("event_type")
            step_name = payload.get("active_step_name") or payload.get("step_name") or "unknown"

            if event_type == "workflow_supervisor_opened":
                opens_by_step[step_name] += 1
            elif event_type == "recovery_hint_actioned":
                hint_actions_by_step[step_name] += 1

        steps_by_name = {step.name for step in steps}
        step_names = steps_by_name | set(opens_by_step) | set(hint_actions_by_step)
        patterns = []

        for step_name in step_names:
            opens = opens_by_step[step_name]
            hint_actions = hint_actions_by_step[step_name]
            patterns.append({
                "step_name": step_name,
                "views": opens,
                "hint_actions": hint_actions,
                "hint_action_rate": cls._rate(hint_actions, opens),
                "confidence": cls._confidence(opens),
                "interpretation": cls._explanation_interpretation(opens, hint_actions),
            })

        return sorted(
            patterns,
            key=lambda item: (item["confidence"] == "insufficient", -item["hint_action_rate"], -item["views"]),
        )[:8]

    @classmethod
    def _ats_patterns(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        replay_events: list[SystemEvent],
        report_events: list[SystemEvent],
        termination_events: list[SystemEvent],
    ) -> list[dict[str, Any]]:
        workflow_by_id = {workflow.id: workflow for workflow in workflows}
        platform_counts: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "workflows": 0,
            "steps": 0,
            "completed_workflows": 0,
            "failed_workflows": 0,
            "human_interventions": 0,
            "replays": 0,
            "reports": 0,
            "terminations": 0,
        })

        for workflow in workflows:
            platform = workflow.platform_type or "Generic"
            platform_counts[platform]["workflows"] += 1
            if workflow.status == WorkflowStatus.COMPLETED:
                platform_counts[platform]["completed_workflows"] += 1
            elif workflow.status == WorkflowStatus.FAILED:
                platform_counts[platform]["failed_workflows"] += 1

        for step in steps:
            workflow = workflow_by_id.get(step.workflow_id)
            platform = workflow.platform_type if workflow and workflow.platform_type else "Generic"
            platform_counts[platform]["steps"] += 1
            output = step.output_data or {}
            if (
                step.status == WorkflowStatus.PAUSED_FOR_HUMAN
                or output.get("human_resolved")
                or output.get("approved_by_user")
            ):
                platform_counts[platform]["human_interventions"] += 1

        for event in replay_events:
            platform = cls._platform_for_event(event, workflow_by_id)
            platform_counts[platform]["replays"] += 1

        for event in report_events:
            platform = cls._platform_for_event(event, workflow_by_id)
            platform_counts[platform]["reports"] += 1

        for event in termination_events:
            platform = cls._platform_for_event(event, workflow_by_id)
            platform_counts[platform]["terminations"] += 1

        patterns = []
        for platform, counts in platform_counts.items():
            workflows = counts["workflows"]
            friction_score = min(
                100,
                round(
                    cls._rate(counts["failed_workflows"], workflows) * 0.25
                    + cls._rate(counts["human_interventions"], counts["steps"]) * 0.25
                    + cls._rate(counts["replays"], workflows) * 0.2
                    + cls._rate(counts["reports"], workflows) * 0.15
                    + cls._rate(counts["terminations"], workflows) * 0.15,
                    2,
                ),
            )

            patterns.append({
                "platform": platform,
                "workflows": workflows,
                "confidence": cls._confidence(workflows),
                "friction_score": friction_score,
                "completion_rate": cls._rate(counts["completed_workflows"], workflows),
                "failure_rate": cls._rate(counts["failed_workflows"], workflows),
                "interventions_per_workflow": round(counts["human_interventions"] / workflows, 2) if workflows else 0,
                "replays_per_workflow": round(counts["replays"] / workflows, 2) if workflows else 0,
                "reports_per_workflow": round(counts["reports"] / workflows, 2) if workflows else 0,
                "terminations_per_workflow": round(counts["terminations"] / workflows, 2) if workflows else 0,
            })

        return sorted(
            patterns,
            key=lambda item: (item["confidence"] == "insufficient", -item["friction_score"]),
        )[:8]

    @classmethod
    def _intervention_fatigue(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
    ) -> dict[str, Any]:
        workflow_ids = {workflow.id for workflow in workflows}
        interventions_by_workflow: Counter[int] = Counter()
        successful_workflows = {
            workflow.id for workflow in workflows
            if workflow.status == WorkflowStatus.COMPLETED
        }

        for step in steps:
            output = step.output_data or {}
            if (
                step.workflow_id in workflow_ids
                and (
                    step.status == WorkflowStatus.PAUSED_FOR_HUMAN
                    or output.get("human_resolved")
                    or output.get("approved_by_user")
                )
            ):
                interventions_by_workflow[step.workflow_id] += 1

        total_interventions = sum(interventions_by_workflow.values())
        total_workflows = len(workflows)
        successful_count = len(successful_workflows)
        high_fatigue_workflows = len([
            workflow_id for workflow_id, count in interventions_by_workflow.items()
            if count >= 3
        ])

        return {
            "total_interventions": total_interventions,
            "interventions_per_workflow": round(total_interventions / total_workflows, 2) if total_workflows else 0,
            "interventions_per_successful_application": round(
                sum(interventions_by_workflow[workflow_id] for workflow_id in successful_workflows) / successful_count,
                2,
            ) if successful_count else 0,
            "high_fatigue_workflows": high_fatigue_workflows,
            "confidence": cls._confidence(total_workflows),
            "risk_level": cls._fatigue_risk(total_interventions, total_workflows, high_fatigue_workflows),
        }

    @classmethod
    def _trust_decay(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        termination_events: list[SystemEvent],
    ) -> dict[str, Any]:
        steps_by_workflow: dict[int, list[WorkflowStep]] = defaultdict(list)
        for step in steps:
            steps_by_workflow[step.workflow_id].append(step)

        failed_recoveries_before_termination: list[int] = []
        for event in termination_events:
            workflow_id = (event.payload or {}).get("workflow_id")
            if not workflow_id:
                continue

            workflow_steps = steps_by_workflow.get(workflow_id, [])
            failed_recoveries_before_termination.append(
                len([
                    step for step in workflow_steps
                    if step.attempts and step.attempts > 1 and step.status != WorkflowStatus.COMPLETED
                ])
            )

        termination_count = len(termination_events)
        average_failed_recoveries = (
            sum(failed_recoveries_before_termination) / len(failed_recoveries_before_termination)
        ) if failed_recoveries_before_termination else 0

        return {
            "terminated_workflows": termination_count,
            "termination_rate": cls._rate(termination_count, len(workflows)),
            "average_failed_recoveries_before_termination": round(average_failed_recoveries, 2),
            "confidence": cls._confidence(len(workflows)),
            "risk_level": cls._trust_risk(termination_count, len(workflows), average_failed_recoveries),
        }

    @classmethod
    def _summary(
        cls,
        node_patterns: list[dict[str, Any]],
        ats_patterns: list[dict[str, Any]],
        intervention_fatigue: dict[str, Any],
        trust_decay: dict[str, Any],
    ) -> dict[str, Any]:
        top_node = node_patterns[0] if node_patterns else None
        top_platform = ats_patterns[0] if ats_patterns else None

        return {
            "top_confusion_node": top_node["step_name"] if top_node else None,
            "top_confusion_node_confidence": top_node["confidence"] if top_node else "insufficient",
            "highest_friction_platform": top_platform["platform"] if top_platform else None,
            "highest_friction_platform_confidence": top_platform["confidence"] if top_platform else "insufficient",
            "fatigue_risk_level": intervention_fatigue["risk_level"],
            "trust_decay_risk_level": trust_decay["risk_level"],
        }

    @classmethod
    def _node_recommendation(cls, counts: dict[str, Any], observations: int) -> str:
        confidence = cls._confidence(observations)
        if confidence == "insufficient":
            return "Observe only until more samples are available."
        if counts["terminations"] > 0:
            return "Review checkpoint copy and recovery semantics before changing automation policy."
        if counts["reports"] > 0:
            return "Review explanation clarity and data-used disclosure."
        if counts["replays"] > 0 or counts["repeated_retries"] > 0:
            return "Inspect replay reliability and recovery hint quality."
        if counts["human_interventions"] > observations * 0.5:
            return "Monitor intervention fatigue; do not remove approval gates without review."
        return "No pattern action recommended."

    @staticmethod
    def _explanation_interpretation(views: int, hint_actions: int) -> str:
        if views == 0:
            return "No supervisor views observed."
        if hint_actions == 0:
            return "Explanations are viewed but have not yet led to recovery actions."
        return "Recovery hints are being used; compare with replay outcomes before editing copy."

    @staticmethod
    def _platform_for_event(event: SystemEvent, workflow_by_id: dict[int, ApplicationWorkflow]) -> str:
        workflow_id = (event.payload or {}).get("workflow_id")
        workflow = workflow_by_id.get(workflow_id)
        return workflow.platform_type if workflow and workflow.platform_type else "Generic"

    @classmethod
    def _confidence(cls, sample_size: int) -> str:
        if sample_size >= cls.STABLE_SAMPLE_SIZE:
            return "stable"
        if sample_size >= cls.DIRECTIONAL_SAMPLE_SIZE:
            return "directional"
        return "insufficient"

    @staticmethod
    def _events(events: list[SystemEvent], event_type: EventType) -> list[SystemEvent]:
        return [event for event in events if event.event_type == event_type.value]

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float:
        return round((numerator / denominator * 100), 2) if denominator else 0

    @staticmethod
    def _fatigue_risk(total_interventions: int, total_workflows: int, high_fatigue_workflows: int) -> str:
        if not total_workflows:
            return "unknown"

        interventions_per_workflow = total_interventions / total_workflows
        high_fatigue_rate = high_fatigue_workflows / total_workflows

        if interventions_per_workflow >= 2 or high_fatigue_rate >= 0.25:
            return "high"
        if interventions_per_workflow >= 1:
            return "medium"
        return "low"

    @staticmethod
    def _trust_risk(termination_count: int, total_workflows: int, average_failed_recoveries: float) -> str:
        if not total_workflows:
            return "unknown"

        termination_rate = termination_count / total_workflows
        if termination_rate >= 0.25 or average_failed_recoveries >= 2:
            return "high"
        if termination_rate >= 0.1 or average_failed_recoveries >= 1:
            return "medium"
        return "low"
