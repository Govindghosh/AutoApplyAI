from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.event import SystemEvent
from app.models.health import SelectorHealth
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.services.event_service import EventType


class ReliabilityOptimizationService:
    """
    Phase 31 reliability and resource efficiency analytics.

    These outputs are advisory scheduling intelligence. They make queue,
    browser, replay, and intervention costs visible without mutating workflow
    ordering behind the user's back.
    """

    BROWSER_MEMORY_BASE_MB = 180
    BROWSER_MEMORY_PER_ACTIVE_STEP_MB = 45
    MAX_BROWSER_LIFETIME_WORKFLOWS = 12
    TARGET_CONCURRENCY = 4

    @classmethod
    def build(cls, db: Session, user_id: int) -> dict[str, Any]:
        workflows = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.user_id == user_id).all()
        steps = db.query(WorkflowStep).join(ApplicationWorkflow).filter(ApplicationWorkflow.user_id == user_id).all()
        events = db.query(SystemEvent).filter(SystemEvent.user_id == user_id).all()
        selector_health = db.query(SelectorHealth).all()

        steps_by_workflow: dict[int, list[WorkflowStep]] = defaultdict(list)
        for step in steps:
            steps_by_workflow[step.workflow_id].append(step)

        return {
            "browser_resource_scheduler": cls._browser_resource_scheduler(workflows, steps),
            "adaptive_queue_prioritization": cls._adaptive_queue(workflows, steps_by_workflow),
            "reliability_scoring_v2": cls._reliability_scores(workflows, steps, selector_health),
            "replay_optimization": cls._replay_optimization(workflows, steps, events),
            "intervention_cost": cls._intervention_cost(workflows, steps, events),
            "workflow_throughput": cls._throughput(workflows, steps),
            "guardrails": {
                "note": "Optimization recommendations are explainable and do not bypass approval or recovery semantics.",
                "forbidden_shortcuts": [
                    "skip final approval",
                    "mutate recovery state invisibly",
                    "reuse browser state across users",
                    "prioritize queues without starvation protection",
                ],
            },
        }

    @classmethod
    def _browser_resource_scheduler(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
    ) -> dict[str, Any]:
        active_workflows = [workflow for workflow in workflows if workflow.status == WorkflowStatus.RUNNING]
        active_steps = [step for step in steps if step.status == WorkflowStatus.RUNNING]
        platform_counts = Counter((workflow.platform_type or "Generic") for workflow in workflows)
        active_by_platform = Counter((workflow.platform_type or "Generic") for workflow in active_workflows)
        estimated_memory = (
            cls.BROWSER_MEMORY_BASE_MB * max(len(active_workflows), 1)
            + cls.BROWSER_MEMORY_PER_ACTIVE_STEP_MB * len(active_steps)
            if active_workflows
            else 0
        )
        tab_saturation = round((len(active_steps) / max(len(active_workflows), 1)) * 100, 2) if active_workflows else 0

        ats_cost = [
            {
                "platform": platform,
                "workflow_count": count,
                "active": active_by_platform[platform],
                "resource_cost_units": count + active_by_platform[platform] * 3,
            }
            for platform, count in platform_counts.most_common()
        ]

        crash_risk = "high" if estimated_memory > 1400 or tab_saturation > 250 else "medium" if estimated_memory > 800 else "low"
        recommended_concurrency = max(1, min(cls.TARGET_CONCURRENCY, 6 - len(active_workflows)))

        return {
            "memory_usage_mb_estimate": estimated_memory,
            "browser_lifetime_policy": {
                "max_workflows_before_recycle": cls.MAX_BROWSER_LIFETIME_WORKFLOWS,
                "recycle_on_crash_risk": crash_risk in ["medium", "high"],
            },
            "tab_saturation_percent": tab_saturation,
            "ats_resource_cost": ats_cost,
            "adaptive_concurrency": {
                "current_active": len(active_workflows),
                "recommended_new_capacity": recommended_concurrency,
                "crash_risk": crash_risk,
            },
            "pooling_policy": "pool by user and ATS, never across users",
        }

    @classmethod
    def _adaptive_queue(
        cls,
        workflows: list[ApplicationWorkflow],
        steps_by_workflow: dict[int, list[WorkflowStep]],
    ) -> dict[str, Any]:
        queue_items = []
        for workflow in workflows:
            steps = steps_by_workflow.get(workflow.id, [])
            paused = len([step for step in steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN])
            failed = len([step for step in steps if step.status == WorkflowStatus.FAILED])
            replay = len([step for step in steps if (step.attempts or 0) > 1])
            ats_sensitive = 1 if (workflow.platform_type or "").lower() in ["greenhouse", "lever"] else 0
            priority = 40
            priority += paused * 25
            priority += failed * 20
            priority += replay * 10
            priority += ats_sensitive * 5
            if workflow.status == WorkflowStatus.PENDING:
                priority += 5

            queue_items.append(
                {
                    "workflow_id": workflow.id,
                    "platform": workflow.platform_type or "Generic",
                    "status": workflow.status.value if hasattr(workflow.status, "value") else str(workflow.status),
                    "priority_score": min(priority, 100),
                    "priority_reasons": cls._priority_reasons(paused, failed, replay, ats_sensitive),
                }
            )

        return {
            "policy": "approval and recovery work first, with age-based starvation protection",
            "starvation_prevention": "increase priority after every scheduler pass with no execution",
            "queues": sorted(queue_items, key=lambda item: item["priority_score"], reverse=True)[:20],
        }

    @staticmethod
    def _priority_reasons(paused: int, failed: int, replay: int, ats_sensitive: int) -> list[str]:
        reasons = []
        if paused:
            reasons.append("human_escalated")
        if failed:
            reasons.append("replay_recovery")
        if replay:
            reasons.append("replay_history")
        if ats_sensitive:
            reasons.append("ats_sensitive")
        return reasons or ["normal"]

    @classmethod
    def _reliability_scores(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        selector_health: list[SelectorHealth],
    ) -> dict[str, Any]:
        by_step = Counter(step.name for step in steps)
        failed_by_step = Counter(step.name for step in steps if step.status == WorkflowStatus.FAILED)
        paused_by_step = Counter(step.name for step in steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN)
        replay_by_step = Counter(step.name for step in steps if (step.attempts or 0) > 1)

        node_scores = []
        for step_name, total in by_step.items():
            failure_rate = failed_by_step[step_name] / max(total, 1)
            escalation_rate = paused_by_step[step_name] / max(total, 1)
            replay_rate = replay_by_step[step_name] / max(total, 1)
            score = round(max(0, 100 - failure_rate * 45 - escalation_rate * 30 - replay_rate * 20), 2)
            node_scores.append(
                {
                    "node": step_name,
                    "score": score,
                    "failure_rate": round(failure_rate * 100, 2),
                    "escalation_probability": round(escalation_rate * 100, 2),
                    "replay_consistency": round((1 - replay_rate) * 100, 2),
                }
            )

        workflows_by_platform = Counter((workflow.platform_type or "Generic") for workflow in workflows)
        failed_by_platform = Counter(
            (workflow.platform_type or "Generic")
            for workflow in workflows
            if workflow.status == WorkflowStatus.FAILED
        )
        health_by_platform: dict[str, list[SelectorHealth]] = defaultdict(list)
        for health in selector_health:
            health_by_platform[health.platform or "Generic"].append(health)

        ats_scores = []
        for platform, count in workflows_by_platform.items():
            selector_scores = [health.success_rate for health in health_by_platform.get(platform, []) if health.success_rate is not None]
            selector_score = sum(selector_scores) / len(selector_scores) if selector_scores else 1
            failure_rate = failed_by_platform[platform] / max(count, 1)
            score = round(max(0, selector_score * 100 - failure_rate * 35), 2)
            ats_scores.append(
                {
                    "platform": platform,
                    "score": score,
                    "selector_health": round(selector_score * 100, 2),
                    "workflow_failure_rate": round(failure_rate * 100, 2),
                    "intervention_likelihood": cls._platform_intervention_likelihood(platform, workflows, steps),
                }
            )

        return {
            "node_stability": sorted(node_scores, key=lambda item: item["score"]),
            "ats_reliability": sorted(ats_scores, key=lambda item: item["score"]),
            "fragility_prediction": cls._fragility_prediction(node_scores, ats_scores),
        }

    @staticmethod
    def _platform_intervention_likelihood(
        platform: str,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
    ) -> float:
        workflow_ids = {
            workflow.id
            for workflow in workflows
            if (workflow.platform_type or "Generic") == platform
        }
        platform_steps = [step for step in steps if step.workflow_id in workflow_ids]
        if not platform_steps:
            return 0
        interventions = len([step for step in platform_steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN])
        return round((interventions / len(platform_steps)) * 100, 2)

    @staticmethod
    def _fragility_prediction(
        node_scores: list[dict[str, Any]],
        ats_scores: list[dict[str, Any]],
    ) -> dict[str, Any]:
        weakest_node = node_scores[0] if node_scores else None
        weakest_ats = ats_scores[0] if ats_scores else None
        risk_score = 0
        if weakest_node:
            risk_score += max(0, 100 - weakest_node["score"]) * 0.5
        if weakest_ats:
            risk_score += max(0, 100 - weakest_ats["score"]) * 0.5
        return {
            "risk_score": round(risk_score, 2),
            "level": "high" if risk_score >= 50 else "medium" if risk_score >= 25 else "low",
            "weakest_node": weakest_node,
            "weakest_ats": weakest_ats,
        }

    @classmethod
    def _replay_optimization(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        events: list[SystemEvent],
    ) -> dict[str, Any]:
        replay_steps = [step for step in steps if (step.attempts or 0) > 1]
        replay_events = [event for event in events if event.event_type == EventType.WORKFLOW_CHECKPOINT_REPLAYED.value]
        completed_replays = [step for step in replay_steps if step.status == WorkflowStatus.COMPLETED]
        replay_durations = [step.duration_ms for step in completed_replays if step.duration_ms]
        redundant_navigation = len([
            step for step in replay_steps
            if step.name == "NAVIGATE_TO_JOB"
        ])
        divergence = len([
            step for step in replay_steps
            if step.status == WorkflowStatus.FAILED and (step.attempts or 0) > 2
        ])

        return {
            "replay_latency_ms": round(sum(replay_durations) / len(replay_durations), 2) if replay_durations else 0,
            "replay_path_cache_candidates": cls._replay_cache_candidates(replay_steps),
            "redundant_navigation_count": redundant_navigation,
            "browser_warm_state_reuse": "recommended_for_same_user_same_ats_within_session",
            "checkpoint_hydration_speed": "fast" if replay_durations and max(replay_durations) < 30000 else "unknown",
            "deterministic_replay_tracing": len(replay_events),
            "replay_divergence_detection": {
                "divergent_replays": divergence,
                "rate": round((divergence / max(len(replay_steps), 1)) * 100, 2),
            },
        }

    @staticmethod
    def _replay_cache_candidates(replay_steps: list[WorkflowStep]) -> list[dict[str, Any]]:
        counts = Counter(step.name for step in replay_steps)
        return [
            {
                "step_name": step_name,
                "replay_count": count,
                "cache": "checkpoint_hydration",
            }
            for step_name, count in counts.most_common()
            if count > 1
        ][:8]

    @classmethod
    def _intervention_cost(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        events: list[SystemEvent],
    ) -> dict[str, Any]:
        escalated = [step for step in steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN]
        approvals = [step for step in steps if step.name == "SUBMIT_APPLICATION"]
        replay_events = [event for event in events if event.event_type == EventType.WORKFLOW_CHECKPOINT_REPLAYED.value]
        terminations = [event for event in events if event.event_type == EventType.WORKFLOW_TERMINATED.value]
        minutes = sum(cls._step_minutes(step) for step in escalated)

        return {
            "minutes_per_escalation": round(minutes / len(escalated), 2) if escalated else 0,
            "approvals_per_workflow": round(len(approvals) / max(len(workflows), 1), 2),
            "replay_fatigue": round(len(replay_events) / max(len(workflows), 1), 2),
            "intervention_abandonment": len(terminations),
            "estimated_human_cost_minutes": round(minutes, 2),
        }

    @classmethod
    def _throughput(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
    ) -> dict[str, Any]:
        completed_workflows = [workflow for workflow in workflows if workflow.status == WorkflowStatus.COMPLETED]
        durations = cls._workflow_durations(workflows, steps)
        active = len([workflow for workflow in workflows if workflow.status == WorkflowStatus.RUNNING])
        queued = len([workflow for workflow in workflows if workflow.status == WorkflowStatus.PENDING])
        bottlenecks = cls._node_bottlenecks(steps)

        return {
            "workflow_completion_duration_seconds": round(sum(durations) / len(durations), 2) if durations else 0,
            "completed_workflows": len(completed_workflows),
            "active_workflows": active,
            "queued_workflows": queued,
            "node_bottlenecks": bottlenecks,
            "queue_pressure": round(((active + queued) / max(len(workflows), 1)) * 100, 2),
            "concurrency_saturation": round((active / max(cls.TARGET_CONCURRENCY, 1)) * 100, 2),
        }

    @staticmethod
    def _workflow_durations(
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
    ) -> list[float]:
        steps_by_workflow: dict[int, list[WorkflowStep]] = defaultdict(list)
        for step in steps:
            steps_by_workflow[step.workflow_id].append(step)

        durations = []
        for workflow in workflows:
            workflow_steps = steps_by_workflow.get(workflow.id, [])
            started = [
                ReliabilityOptimizationService._aware(step.started_at)
                for step in workflow_steps
                if step.started_at
            ]
            completed = [
                ReliabilityOptimizationService._aware(step.completed_at)
                for step in workflow_steps
                if step.completed_at
            ]
            if started and completed:
                durations.append((max(completed) - min(started)).total_seconds())
        return durations

    @staticmethod
    def _node_bottlenecks(steps: list[WorkflowStep]) -> list[dict[str, Any]]:
        durations_by_step: dict[str, list[int]] = defaultdict(list)
        for step in steps:
            if step.duration_ms:
                durations_by_step[step.name].append(step.duration_ms)
        bottlenecks = []
        for step_name, durations in durations_by_step.items():
            bottlenecks.append(
                {
                    "step_name": step_name,
                    "avg_duration_ms": round(sum(durations) / len(durations), 2),
                    "samples": len(durations),
                }
            )
        return sorted(bottlenecks, key=lambda item: item["avg_duration_ms"], reverse=True)[:8]

    @staticmethod
    def _step_minutes(step: WorkflowStep) -> float:
        if step.started_at and step.completed_at:
            return (
                ReliabilityOptimizationService._aware(step.completed_at)
                - ReliabilityOptimizationService._aware(step.started_at)
            ).total_seconds() / 60
        if step.started_at and step.status == WorkflowStatus.PAUSED_FOR_HUMAN:
            return (
                datetime.now(timezone.utc)
                - ReliabilityOptimizationService._aware(step.started_at)
            ).total_seconds() / 60
        return 0

    @staticmethod
    def _aware(value: datetime | None) -> datetime:
        if not value:
            return datetime.fromtimestamp(0, tz=timezone.utc)
        if value.tzinfo:
            return value
        return value.replace(tzinfo=timezone.utc)
