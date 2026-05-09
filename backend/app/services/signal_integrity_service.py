from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from math import exp, log
from typing import Any

from sqlalchemy.orm import Session

from app.models.event import SystemEvent
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.services.event_service import EventType


class SignalIntegrityService:
    MIN_OBSERVE_SAMPLE = 5
    MIN_DIRECTIONAL_SAMPLE = 20
    MIN_STABLE_SAMPLE = 50
    RECENT_WINDOW_DAYS = 7
    BASELINE_WINDOW_DAYS = 21
    DECAY_HALF_LIFE_DAYS = 14

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
        events_by_type = Counter(event.event_type for event in events)

        sample_quality = cls._sample_quality(workflows, steps, events, events_by_type)
        temporal_stability = cls._temporal_stability(workflows, steps, events)
        signal_decay = cls._signal_decay(workflows, events)
        segment_analysis = cls._segment_analysis(workflows, steps, events)
        causation_guards = cls._causation_guards(
            workflows,
            steps,
            events,
            workflow_by_id,
            temporal_stability,
            sample_quality,
        )

        return {
            "guardrails": {
                "note": (
                    "Phase 26 validates signal quality before interpretation. These checks "
                    "do not mutate orchestration policy."
                ),
                "minimums": {
                    "observe": cls.MIN_OBSERVE_SAMPLE,
                    "directional": cls.MIN_DIRECTIONAL_SAMPLE,
                    "stable": cls.MIN_STABLE_SAMPLE,
                },
                "temporal_windows_days": {
                    "recent": cls.RECENT_WINDOW_DAYS,
                    "baseline": cls.BASELINE_WINDOW_DAYS,
                },
                "decay_half_life_days": cls.DECAY_HALF_LIFE_DAYS,
            },
            "sample_quality": sample_quality,
            "temporal_stability": temporal_stability,
            "causation_guards": causation_guards,
            "segment_analysis": segment_analysis,
            "signal_decay": signal_decay,
            "summary": cls._summary(sample_quality, temporal_stability, causation_guards, signal_decay),
        }

    @classmethod
    def _sample_quality(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        events: list[SystemEvent],
        events_by_type: Counter[str],
    ) -> dict[str, Any]:
        workflow_count = len(workflows)
        step_count = len(steps)
        event_count = len(events)
        replay_count = events_by_type[EventType.WORKFLOW_CHECKPOINT_REPLAYED.value]
        report_count = events_by_type[EventType.WORKFLOW_NODE_REPORTED.value]
        termination_count = events_by_type[EventType.WORKFLOW_TERMINATED.value]
        product_signal_count = events_by_type[EventType.PRODUCT_TELEMETRY.value]
        platforms = Counter((workflow.platform_type or "Generic") for workflow in workflows)
        platform_coverage = [
            {
                "platform": platform,
                "workflows": count,
                "confidence": cls._confidence(count),
            }
            for platform, count in platforms.most_common()
        ]

        metric_samples = [
            cls._metric_quality("workflow_patterns", workflow_count),
            cls._metric_quality("node_patterns", step_count),
            cls._metric_quality("replay_patterns", replay_count),
            cls._metric_quality("report_patterns", report_count),
            cls._metric_quality("termination_patterns", termination_count),
            cls._metric_quality("explanation_patterns", product_signal_count),
        ]

        blockers = [
            metric["metric"]
            for metric in metric_samples
            if metric["confidence"] == "insufficient"
        ]

        return {
            "overall_confidence": cls._confidence(min(workflow_count, step_count)),
            "workflows": workflow_count,
            "steps": step_count,
            "events": event_count,
            "metric_samples": metric_samples,
            "platform_coverage": platform_coverage,
            "interpretation": cls._sample_interpretation(blockers),
        }

    @classmethod
    def _temporal_stability(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        events: list[SystemEvent],
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        recent_start = now - timedelta(days=cls.RECENT_WINDOW_DAYS)
        baseline_start = now - timedelta(days=cls.BASELINE_WINDOW_DAYS)

        recent_workflows = [
            workflow for workflow in workflows
            if cls._after(workflow.created_at, recent_start)
        ]
        baseline_workflows = [
            workflow for workflow in workflows
            if cls._between(workflow.created_at, baseline_start, recent_start)
        ]
        recent_events = [
            event for event in events
            if cls._after(event.timestamp, recent_start)
        ]
        baseline_events = [
            event for event in events
            if cls._between(event.timestamp, baseline_start, recent_start)
        ]

        recent_metrics = cls._window_metrics(recent_workflows, recent_events)
        baseline_metrics = cls._window_metrics(baseline_workflows, baseline_events)
        comparisons = []

        for key in ["workflow_failure_rate", "replay_rate", "termination_rate", "report_rate"]:
            recent_value = recent_metrics[key]
            baseline_value = baseline_metrics[key]
            delta = round(recent_value - baseline_value, 2)
            comparisons.append({
                "metric": key,
                "recent": recent_value,
                "baseline": baseline_value,
                "delta": delta,
                "stability": cls._stability_label(
                    len(recent_workflows),
                    len(baseline_workflows),
                    delta,
                ),
            })

        volatile_metrics = [
            comparison["metric"]
            for comparison in comparisons
            if comparison["stability"] == "volatile"
        ]

        return {
            "recent_window_days": cls.RECENT_WINDOW_DAYS,
            "baseline_window_days": cls.BASELINE_WINDOW_DAYS,
            "recent_samples": len(recent_workflows),
            "baseline_samples": len(baseline_workflows),
            "comparisons": comparisons,
            "overall_stability": "volatile" if volatile_metrics else (
                "insufficient" if not recent_workflows or not baseline_workflows else "stable"
            ),
            "interpretation": cls._temporal_interpretation(volatile_metrics, recent_workflows, baseline_workflows),
        }

    @classmethod
    def _causation_guards(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        events: list[SystemEvent],
        workflow_by_id: dict[int, ApplicationWorkflow],
        temporal_stability: dict[str, Any],
        sample_quality: dict[str, Any],
    ) -> list[dict[str, Any]]:
        guards: list[dict[str, Any]] = []
        platform_friction = cls._platform_friction(workflows, steps, events, workflow_by_id)
        high_platforms = [
            platform for platform in platform_friction
            if platform["confidence"] != "insufficient" and platform["friction_score"] >= 40
        ]

        if high_platforms:
            guards.append({
                "signal": "high_replay_or_termination_rate",
                "possible_confounder": "platform_specific_friction",
                "severity": "medium",
                "confidence": high_platforms[0]["confidence"],
                "guardrail": (
                    "Do not attribute replay or termination spikes to explanation quality "
                    "until ATS/platform friction is reviewed."
                ),
            })

        if temporal_stability["overall_stability"] == "volatile":
            guards.append({
                "signal": "recent_metric_spike",
                "possible_confounder": "temporary_operational_noise",
                "severity": "medium",
                "confidence": "directional",
                "guardrail": (
                    "Treat current spike as temporal noise until it persists across another "
                    "observation window."
                ),
            })

        report_count = len(cls._events(events, EventType.WORKFLOW_NODE_REPORTED))
        replay_count = len(cls._events(events, EventType.WORKFLOW_CHECKPOINT_REPLAYED))
        if report_count > 0 and replay_count == 0:
            guards.append({
                "signal": "reported_nodes_without_replay",
                "possible_confounder": "user_uncertainty_or_support_behavior",
                "severity": "low",
                "confidence": sample_quality["overall_confidence"],
                "guardrail": (
                    "Reports alone indicate review interest, not necessarily broken recovery "
                    "semantics."
                ),
            })

        product_events = cls._events(events, EventType.PRODUCT_TELEMETRY)
        supervisor_views = len([
            event for event in product_events
            if (event.payload or {}).get("event_type") == "workflow_supervisor_opened"
        ])
        hint_actions = len([
            event for event in product_events
            if (event.payload or {}).get("event_type") == "recovery_hint_actioned"
        ])
        if supervisor_views < cls.MIN_OBSERVE_SAMPLE and hint_actions == 0:
            guards.append({
                "signal": "low_hint_action_rate",
                "possible_confounder": "insufficient_explanation_exposure",
                "severity": "low",
                "confidence": "insufficient",
                "guardrail": (
                    "Do not rewrite recovery hints until enough users have seen them."
                ),
            })

        if not guards:
            guards.append({
                "signal": "none_detected",
                "possible_confounder": "none_detected",
                "severity": "low",
                "confidence": sample_quality["overall_confidence"],
                "guardrail": "No causation guard triggered; continue observational review.",
            })

        return guards

    @classmethod
    def _segment_analysis(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        events: list[SystemEvent],
    ) -> dict[str, Any]:
        workflow_count = len(workflows)
        intervention_steps = [
            step for step in steps
            if step.status == WorkflowStatus.PAUSED_FOR_HUMAN
            or (step.output_data or {}).get("human_resolved")
            or (step.output_data or {}).get("approved_by_user")
        ]
        replay_count = len(cls._events(events, EventType.WORKFLOW_CHECKPOINT_REPLAYED))
        report_count = len(cls._events(events, EventType.WORKFLOW_NODE_REPORTED))
        termination_count = len(cls._events(events, EventType.WORKFLOW_TERMINATED))
        interventions_per_workflow = round(len(intervention_steps) / workflow_count, 2) if workflow_count else 0

        if workflow_count >= 30:
            volume_segment = "high_volume"
        elif workflow_count >= 10:
            volume_segment = "power_user"
        elif workflow_count >= 1:
            volume_segment = "novice_or_early_beta"
        else:
            volume_segment = "no_usage"

        behavior_flags = []
        if interventions_per_workflow >= 2:
            behavior_flags.append("intervention_heavy")
        if replay_count >= workflow_count and workflow_count > 0:
            behavior_flags.append("replay_heavy")
        if termination_count > 0:
            behavior_flags.append("termination_exposed")
        if report_count > replay_count:
            behavior_flags.append("support_or_confusion_reporting")

        return {
            "current_user_segment": volume_segment,
            "behavior_flags": behavior_flags or ["no_strong_segment_signal"],
            "workflows": workflow_count,
            "interventions_per_workflow": interventions_per_workflow,
            "replays": replay_count,
            "reports": report_count,
            "terminations": termination_count,
            "aggregate_caveat": (
                "This endpoint is user-scoped. Cross-user cohort comparison should be "
                "added only with explicit admin/privacy boundaries."
            ),
        }

    @classmethod
    def _signal_decay(
        cls,
        workflows: list[ApplicationWorkflow],
        events: list[SystemEvent],
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        raw_workflow_count = len(workflows)
        raw_event_count = len(events)
        weighted_workflows = sum(
            cls._decay_weight(workflow.created_at, now)
            for workflow in workflows
        )
        weighted_events = sum(
            cls._decay_weight(event.timestamp, now)
            for event in events
        )
        old_events = [
            event for event in events
            if cls._age_days(event.timestamp, now) > cls.DECAY_HALF_LIFE_DAYS
        ]
        stale_signal_share = cls._rate(len(old_events), raw_event_count)

        return {
            "half_life_days": cls.DECAY_HALF_LIFE_DAYS,
            "raw_workflows": raw_workflow_count,
            "decayed_workflow_weight": round(weighted_workflows, 2),
            "raw_events": raw_event_count,
            "decayed_event_weight": round(weighted_events, 2),
            "stale_signal_share": stale_signal_share,
            "interpretation": cls._decay_interpretation(stale_signal_share),
        }

    @classmethod
    def _summary(
        cls,
        sample_quality: dict[str, Any],
        temporal_stability: dict[str, Any],
        causation_guards: list[dict[str, Any]],
        signal_decay: dict[str, Any],
    ) -> dict[str, Any]:
        optimization_readiness = "observe_only"
        if (
            sample_quality["overall_confidence"] == "stable"
            and temporal_stability["overall_stability"] == "stable"
            and signal_decay["stale_signal_share"] < 50
            and all(guard["severity"] == "low" for guard in causation_guards)
        ):
            optimization_readiness = "review_eligible"
        elif sample_quality["overall_confidence"] == "directional":
            optimization_readiness = "human_review_only"

        return {
            "optimization_readiness": optimization_readiness,
            "overall_confidence": sample_quality["overall_confidence"],
            "temporal_stability": temporal_stability["overall_stability"],
            "causation_guard_count": len([
                guard for guard in causation_guards
                if guard["signal"] != "none_detected"
            ]),
            "stale_signal_share": signal_decay["stale_signal_share"],
        }

    @classmethod
    def _metric_quality(cls, metric: str, sample_size: int) -> dict[str, Any]:
        return {
            "metric": metric,
            "sample_size": sample_size,
            "confidence": cls._confidence(sample_size),
            "minimum_for_directional": cls.MIN_DIRECTIONAL_SAMPLE,
            "minimum_for_stable": cls.MIN_STABLE_SAMPLE,
            "actionability": cls._actionability(sample_size),
        }

    @classmethod
    def _window_metrics(
        cls,
        workflows: list[ApplicationWorkflow],
        events: list[SystemEvent],
    ) -> dict[str, float]:
        workflow_count = len(workflows)
        event_denominator = max(workflow_count, 1)
        failed_workflows = len([
            workflow for workflow in workflows
            if workflow.status == WorkflowStatus.FAILED
        ])

        return {
            "workflow_failure_rate": cls._rate(failed_workflows, workflow_count),
            "replay_rate": cls._rate(
                len(cls._events(events, EventType.WORKFLOW_CHECKPOINT_REPLAYED)),
                event_denominator,
            ),
            "termination_rate": cls._rate(
                len(cls._events(events, EventType.WORKFLOW_TERMINATED)),
                event_denominator,
            ),
            "report_rate": cls._rate(
                len(cls._events(events, EventType.WORKFLOW_NODE_REPORTED)),
                event_denominator,
            ),
        }

    @classmethod
    def _platform_friction(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        events: list[SystemEvent],
        workflow_by_id: dict[int, ApplicationWorkflow],
    ) -> list[dict[str, Any]]:
        platform_counts: dict[str, dict[str, int]] = defaultdict(lambda: {
            "workflows": 0,
            "failed": 0,
            "replays": 0,
            "terminations": 0,
            "reports": 0,
            "interventions": 0,
        })

        for workflow in workflows:
            platform = workflow.platform_type or "Generic"
            platform_counts[platform]["workflows"] += 1
            if workflow.status == WorkflowStatus.FAILED:
                platform_counts[platform]["failed"] += 1

        for step in steps:
            workflow = workflow_by_id.get(step.workflow_id)
            platform = workflow.platform_type if workflow and workflow.platform_type else "Generic"
            if step.status == WorkflowStatus.PAUSED_FOR_HUMAN or (step.output_data or {}).get("human_resolved"):
                platform_counts[platform]["interventions"] += 1

        for event_type, key in [
            (EventType.WORKFLOW_CHECKPOINT_REPLAYED, "replays"),
            (EventType.WORKFLOW_TERMINATED, "terminations"),
            (EventType.WORKFLOW_NODE_REPORTED, "reports"),
        ]:
            for event in cls._events(events, event_type):
                workflow = workflow_by_id.get((event.payload or {}).get("workflow_id"))
                platform = workflow.platform_type if workflow and workflow.platform_type else "Generic"
                platform_counts[platform][key] += 1

        friction = []
        for platform, counts in platform_counts.items():
            workflows_count = counts["workflows"]
            friction.append({
                "platform": platform,
                "confidence": cls._confidence(workflows_count),
                "friction_score": min(
                    100,
                    round(
                        cls._rate(counts["failed"], workflows_count) * 0.3
                        + cls._rate(counts["replays"], workflows_count) * 0.25
                        + cls._rate(counts["terminations"], workflows_count) * 0.25
                        + cls._rate(counts["reports"], workflows_count) * 0.2,
                        2,
                    ),
                ),
            })

        return sorted(friction, key=lambda item: item["friction_score"], reverse=True)

    @classmethod
    def _confidence(cls, sample_size: int) -> str:
        if sample_size >= cls.MIN_STABLE_SAMPLE:
            return "stable"
        if sample_size >= cls.MIN_DIRECTIONAL_SAMPLE:
            return "directional"
        if sample_size >= cls.MIN_OBSERVE_SAMPLE:
            return "observe_only"
        return "insufficient"

    @classmethod
    def _actionability(cls, sample_size: int) -> str:
        confidence = cls._confidence(sample_size)
        if confidence == "stable":
            return "eligible_for_human_review"
        if confidence == "directional":
            return "monitor_before_action"
        return "observe_only"

    @classmethod
    def _stability_label(cls, recent_samples: int, baseline_samples: int, delta: float) -> str:
        if recent_samples < cls.MIN_OBSERVE_SAMPLE or baseline_samples < cls.MIN_OBSERVE_SAMPLE:
            return "insufficient"
        if abs(delta) >= 25:
            return "volatile"
        if abs(delta) >= 10:
            return "drifting"
        return "stable"

    @staticmethod
    def _sample_interpretation(blockers: list[str]) -> str:
        if not blockers:
            return "Core samples meet minimum interpretability thresholds."

        return "Observe only for low-sample metrics: " + ", ".join(blockers[:4])

    @staticmethod
    def _temporal_interpretation(
        volatile_metrics: list[str],
        recent_workflows: list[ApplicationWorkflow],
        baseline_workflows: list[ApplicationWorkflow],
    ) -> str:
        if not recent_workflows or not baseline_workflows:
            return "Temporal comparison needs both recent and baseline workflow samples."
        if volatile_metrics:
            return "Recent changes may be operational noise: " + ", ".join(volatile_metrics)
        return "No major temporal instability detected."

    @staticmethod
    def _decay_interpretation(stale_signal_share: float) -> str:
        if stale_signal_share >= 60:
            return "Most signal is old; treat patterns as stale until recent usage accumulates."
        if stale_signal_share >= 30:
            return "Some signal is aging; prefer recent-window review for policy discussions."
        return "Recent signal share is healthy for observation."

    @staticmethod
    def _events(events: list[SystemEvent], event_type: EventType) -> list[SystemEvent]:
        return [event for event in events if event.event_type == event_type.value]

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float:
        return round((numerator / denominator * 100), 2) if denominator else 0

    @staticmethod
    def _aware(value: datetime | None) -> datetime | None:
        if not value:
            return None
        if value.tzinfo:
            return value
        return value.replace(tzinfo=timezone.utc)

    @classmethod
    def _after(cls, value: datetime | None, start: datetime) -> bool:
        aware = cls._aware(value)
        return bool(aware and aware >= start)

    @classmethod
    def _between(cls, value: datetime | None, start: datetime, end: datetime) -> bool:
        aware = cls._aware(value)
        return bool(aware and start <= aware < end)

    @classmethod
    def _age_days(cls, value: datetime | None, now: datetime) -> float:
        aware = cls._aware(value)
        if not aware:
            return 0
        return max((now - aware).total_seconds() / 86400, 0)

    @classmethod
    def _decay_weight(cls, value: datetime | None, now: datetime) -> float:
        age_days = cls._age_days(value, now)
        if age_days <= 0:
            return 1
        return exp(-log(2) * age_days / cls.DECAY_HALF_LIFE_DAYS)
