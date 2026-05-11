from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models.event import SystemEvent
from app.models.health import SelectorHealth
from app.models.outcome import ApplicationOutcome
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.services.event_service import EventType
from app.services.recovery_service import RecoveryCompressionService


class RecommendationIntelligenceService:
    """
    Phase 32 governed, advisory-only orchestration intelligence.
    """

    DIRECTIONAL_SAMPLE = 5
    STABLE_SAMPLE = 20

    @classmethod
    def build(cls, db: Session, user_id: int) -> dict[str, Any]:
        workflows = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.user_id == user_id).all()
        steps = db.query(WorkflowStep).join(ApplicationWorkflow).filter(ApplicationWorkflow.user_id == user_id).all()
        events = db.query(SystemEvent).filter(SystemEvent.user_id == user_id).all()
        outcomes = db.query(ApplicationOutcome).filter(ApplicationOutcome.user_id == user_id).all()
        selector_health = db.query(SelectorHealth).all()

        steps_by_workflow: dict[int, list[WorkflowStep]] = defaultdict(list)
        for step in steps:
            steps_by_workflow[step.workflow_id].append(step)

        return {
            "workflow_confidence": cls._workflow_confidence(workflows, steps, events, selector_health),
            "resume_variant_recommendations": cls._resume_variant_recommendations(outcomes),
            "ats_strategy": cls._ats_strategy(workflows, steps, outcomes),
            "guided_recovery": cls._guided_recovery(workflows, steps_by_workflow),
            "trust_profiles": cls._trust_profiles(events, steps),
            "recommendation_governance": {
                "authority": "advisory_only",
                "automatic_mutation_allowed": False,
                "required_fields": [
                    "confidence",
                    "sample_quality",
                    "causation_warning",
                    "temporal_stability",
                    "rollback_safety",
                ],
                "guardrails": [
                    "recommendations never edit resumes automatically",
                    "queue and recovery recommendations require governed execution paths",
                    "low-sample recommendations are labeled observe-only",
                    "human approval remains required at submission boundaries",
                ],
            },
        }

    @classmethod
    def _workflow_confidence(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        events: list[SystemEvent],
        selector_health: list[SelectorHealth],
    ) -> dict[str, Any]:
        selector_by_platform: dict[str, list[float]] = defaultdict(list)
        for health in selector_health:
            if health.success_rate is not None:
                selector_by_platform[health.platform or "Generic"].append(health.success_rate)

        replay_events = len([event for event in events if event.event_type == EventType.WORKFLOW_CHECKPOINT_REPLAYED.value])
        termination_events = len([event for event in events if event.event_type == EventType.WORKFLOW_TERMINATED.value])
        escalations = len([step for step in steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN])
        platform_workflows = Counter((workflow.platform_type or "Generic") for workflow in workflows)

        platform_confidence = []
        for platform, count in platform_workflows.items():
            selector_scores = selector_by_platform.get(platform, [1.0])
            selector_score = sum(selector_scores) / len(selector_scores)
            platform_steps = [
                step for step in steps
                if any(workflow.id == step.workflow_id and (workflow.platform_type or "Generic") == platform for workflow in workflows)
            ]
            failed = len([step for step in platform_steps if step.status == WorkflowStatus.FAILED])
            paused = len([step for step in platform_steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN])
            score = selector_score * 100
            score -= (failed / max(len(platform_steps), 1)) * 30
            score -= (paused / max(len(platform_steps), 1)) * 20
            score -= (replay_events / max(len(workflows), 1)) * 5
            level = cls._confidence_level(score, count)
            platform_confidence.append(
                cls._governed_recommendation(
                    recommendation_type="workflow_confidence",
                    target=platform,
                    confidence=level,
                    sample_size=count,
                    message=f"{platform} orchestration confidence is {level}.",
                    action="review_before_execution" if level == "low_confidence" else "normal_governed_execution",
                    raw_score=round(max(0, min(score, 100)), 2),
                )
            )

        return {
            "overall": cls._confidence_level(
                100
                - (escalations / max(len(steps), 1)) * 25
                - (replay_events / max(len(workflows), 1)) * 10
                - termination_events * 5,
                len(workflows),
            ),
            "platforms": platform_confidence,
            "factors": {
                "workflow_samples": len(workflows),
                "selector_health_platforms": len(selector_by_platform),
                "replay_history": replay_events,
                "intervention_frequency": round(escalations / max(len(workflows), 1), 2),
                "user_trust_history": {
                    "terminations": termination_events,
                    "trust_risk": "high" if termination_events > 2 else "normal",
                },
            },
        }

    @classmethod
    def _resume_variant_recommendations(
        cls,
        outcomes: list[ApplicationOutcome],
    ) -> list[dict[str, Any]]:
        by_resume: dict[int | None, list[ApplicationOutcome]] = defaultdict(list)
        for outcome in outcomes:
            by_resume[outcome.resume_id].append(outcome)

        recommendations = []
        for resume_id, resume_outcomes in by_resume.items():
            callbacks = len([
                outcome for outcome in resume_outcomes
                if outcome.status in ["INTERVIEW", "CALLBACK", "OFFER"]
            ])
            total = len(resume_outcomes)
            rate = round((callbacks / total) * 100, 2) if total else 0
            confidence = cls._sample_quality(total)
            recommendations.append(
                cls._governed_recommendation(
                    recommendation_type="resume_variant",
                    target=f"resume:{resume_id or 'base'}",
                    confidence="high_confidence" if rate >= 20 and total >= cls.STABLE_SAMPLE else "medium_confidence" if rate >= 10 and total >= cls.DIRECTIONAL_SAMPLE else "low_confidence",
                    sample_size=total,
                    message=f"Resume variant {resume_id or 'base'} has a {rate}% callback signal.",
                    action="prefer_for_similar_roles" if rate >= 10 else "continue_observing",
                    raw_score=rate,
                    sample_quality=confidence,
                    causation_warning="Outcome data is observational; role mix and market timing may confound callback rate.",
                    rollback_safety="No automatic resume mutation is performed.",
                )
            )

        return sorted(recommendations, key=lambda item: item["raw_score"], reverse=True)

    @classmethod
    def _ats_strategy(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        outcomes: list[ApplicationOutcome],
    ) -> list[dict[str, Any]]:
        outcomes_by_source: dict[str, list[ApplicationOutcome]] = defaultdict(list)
        for outcome in outcomes:
            outcomes_by_source[outcome.job_source or "Generic"].append(outcome)

        workflows_by_platform = Counter((workflow.platform_type or "Generic") for workflow in workflows)
        workflow_ids_by_platform: dict[str, set[int]] = defaultdict(set)
        for workflow in workflows:
            workflow_ids_by_platform[workflow.platform_type or "Generic"].add(workflow.id)

        strategies = []
        for platform, count in workflows_by_platform.items():
            platform_steps = [
                step
                for step in steps
                if step.workflow_id in workflow_ids_by_platform[platform]
            ]
            escalations = len([step for step in platform_steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN])
            failures = len([step for step in platform_steps if step.status == WorkflowStatus.FAILED])
            replay = len([step for step in platform_steps if (step.attempts or 0) > 1])
            source_outcomes = outcomes_by_source.get(platform, [])
            callbacks = len([
                outcome for outcome in source_outcomes
                if outcome.status in ["INTERVIEW", "CALLBACK", "OFFER"]
            ])
            callback_rate = round((callbacks / len(source_outcomes)) * 100, 2) if source_outcomes else 0
            friction = round(((escalations + failures + replay) / max(len(platform_steps), 1)) * 100, 2)
            caution = "high" if friction >= 35 else "medium" if friction >= 15 else "low"

            strategies.append(
                cls._governed_recommendation(
                    recommendation_type="ats_strategy",
                    target=platform,
                    confidence=cls._confidence_level(100 - friction + callback_rate, count),
                    sample_size=count,
                    message=f"{platform} has {friction}% orchestration friction and {callback_rate}% callback signal.",
                    action="prioritize_with_caution" if callback_rate >= 10 and caution != "high" else "use_conservative_mode" if caution == "high" else "continue_observing",
                    raw_score=round(callback_rate - friction, 2),
                    sample_quality=cls._sample_quality(max(count, len(source_outcomes))),
                    causation_warning="ATS completion friction and callback rate are correlated signals, not proof of causation.",
                    rollback_safety="Recommendation only changes operator strategy, not automation policy.",
                    extra={"caution_level": caution, "escalation_expectation": escalations},
                )
            )

        return sorted(strategies, key=lambda item: item["raw_score"], reverse=True)

    @classmethod
    def _guided_recovery(
        cls,
        workflows: list[ApplicationWorkflow],
        steps_by_workflow: dict[int, list[WorkflowStep]],
    ) -> list[dict[str, Any]]:
        recommendations = []
        for workflow in workflows:
            for step in steps_by_workflow.get(workflow.id, []):
                if step.status not in [WorkflowStatus.FAILED, WorkflowStatus.PAUSED_FOR_HUMAN]:
                    continue
                recovery = RecoveryCompressionService.recommend(
                    workflow,
                    step,
                    steps_by_workflow.get(workflow.id, []),
                ).to_dict()
                recommendations.append(
                    cls._governed_recommendation(
                        recommendation_type="guided_recovery",
                        target=f"workflow:{workflow.id}:step:{step.id}",
                        confidence=cls._confidence_from_recovery(recovery["confidence"]),
                        sample_size=step.attempts or 1,
                        message=recovery["reason"],
                        action=recovery["action"],
                        raw_score=recovery["confidence"] * 100,
                        sample_quality="directional",
                        causation_warning="Recovery guidance is based on failure signatures and must preserve checkpoint semantics.",
                        rollback_safety="Replay recommendations reset only the selected incomplete checkpoint.",
                        extra={"recovery": recovery},
                    )
                )

        return recommendations[:12]

    @classmethod
    def _trust_profiles(
        cls,
        events: list[SystemEvent],
        steps: list[WorkflowStep],
    ) -> dict[str, Any]:
        supervisor_opens = len([
            event for event in events
            if event.event_type == EventType.PRODUCT_TELEMETRY.value
            and (event.payload or {}).get("event_type") == "workflow_supervisor_opened"
        ])
        terminations = len([event for event in events if event.event_type == EventType.WORKFLOW_TERMINATED.value])
        paused = len([step for step in steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN])
        replay_steps = len([step for step in steps if (step.attempts or 0) > 1])

        conservative = terminations > 1 or paused > 3
        verbose = supervisor_opens > 2 or replay_steps > 2

        return {
            "current_profile": "conservative_verbose" if conservative and verbose else "conservative" if conservative else "verbose" if verbose else "standard",
            "available_profiles": [
                {
                    "name": "verbose_explainability",
                    "settings": {
                        "explainability_mode": "verbose",
                        "replay_confirmation_sensitivity": "high",
                        "escalation_aggressiveness": "early",
                    },
                },
                {
                    "name": "conservative_automation",
                    "settings": {
                        "explainability_mode": "standard",
                        "replay_confirmation_sensitivity": "high",
                        "escalation_aggressiveness": "early",
                    },
                },
                {
                    "name": "standard",
                    "settings": {
                        "explainability_mode": "standard",
                        "replay_confirmation_sensitivity": "normal",
                        "escalation_aggressiveness": "normal",
                    },
                },
            ],
            "signals": {
                "supervisor_opens": supervisor_opens,
                "terminations": terminations,
                "paused_steps": paused,
                "replay_steps": replay_steps,
            },
        }

    @classmethod
    def _governed_recommendation(
        cls,
        recommendation_type: str,
        target: str,
        confidence: str,
        sample_size: int,
        message: str,
        action: str,
        raw_score: float,
        sample_quality: str | None = None,
        causation_warning: str = "Recommendation is advisory and observational.",
        rollback_safety: str = "No automatic mutation is performed.",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "type": recommendation_type,
            "target": target,
            "confidence": confidence,
            "sample_quality": sample_quality or cls._sample_quality(sample_size),
            "sample_size": sample_size,
            "temporal_stability": "requires_more_time" if sample_size < cls.STABLE_SAMPLE else "stable_enough_for_review",
            "causation_warning": causation_warning,
            "rollback_safety": rollback_safety,
            "message": message,
            "recommended_action": action,
            "raw_score": raw_score,
            "authority": "advisory_only",
            "automatic_mutation_allowed": False,
            **(extra or {}),
        }

    @classmethod
    def _confidence_level(cls, score: float, sample_size: int) -> str:
        if sample_size < cls.DIRECTIONAL_SAMPLE or score < 45:
            return "low_confidence"
        if sample_size < cls.STABLE_SAMPLE or score < 75:
            return "medium_confidence"
        return "high_confidence"

    @classmethod
    def _sample_quality(cls, sample_size: int) -> str:
        if sample_size >= cls.STABLE_SAMPLE:
            return "stable"
        if sample_size >= cls.DIRECTIONAL_SAMPLE:
            return "directional"
        return "insufficient"

    @staticmethod
    def _confidence_from_recovery(confidence: float) -> str:
        if confidence >= 0.85:
            return "high_confidence"
        if confidence >= 0.7:
            return "medium_confidence"
        return "low_confidence"
