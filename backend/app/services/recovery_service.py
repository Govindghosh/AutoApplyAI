from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.services.escalation_service import EscalationCompressionEngine


class RecoveryAction(str, Enum):
    REPLAY_NODE = "replay_node"
    REPLAY_CHECKPOINT = "replay_checkpoint"
    MANUAL_ESCALATION = "manual_escalation"
    TERMINATE_SAFELY = "terminate_safely"


@dataclass(frozen=True)
class RecoveryRecommendation:
    action: RecoveryAction
    confidence: float
    safety_validated: bool
    reason: str
    replay_scope: str
    observability_hooks: tuple[str, ...]
    escalation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["action"] = self.action.value
        return data


class RecoveryCompressionService:
    """
    Maps failure states into the shortest safe recovery path.
    """

    TERMINAL_PATTERNS = (
        "submitted already",
        "duplicate application",
        "application closed",
        "job closed",
        "forbidden",
    )
    HUMAN_PATTERNS = (
        "captcha",
        "verification",
        "login",
        "auth",
        "approval",
        "unknown field",
        "manual",
    )
    ATS_DRIFT_PATTERNS = (
        "selector",
        "element",
        "locator",
        "ats",
        "layout",
    )
    TRANSIENT_PATTERNS = (
        "timeout",
        "network",
        "browser",
        "crash",
        "navigation",
    )

    @classmethod
    def recommend(
        cls,
        workflow: ApplicationWorkflow,
        step: WorkflowStep,
        workflow_steps: list[WorkflowStep] | None = None,
    ) -> RecoveryRecommendation:
        steps = workflow_steps or []
        error = (step.error_log or "").lower()
        attempts = step.attempts or 0
        safety = cls.validate_replay_safety(step, steps)
        loop_risk = attempts >= 3

        if any(pattern in error for pattern in cls.TERMINAL_PATTERNS):
            return RecoveryRecommendation(
                action=RecoveryAction.TERMINATE_SAFELY,
                confidence=0.92,
                safety_validated=True,
                reason="Failure indicates a terminal or duplicate-submission risk.",
                replay_scope="none",
                observability_hooks=("workflow_terminated", "terminal_failure"),
            )

        if any(pattern in error for pattern in cls.HUMAN_PATTERNS) or step.status == WorkflowStatus.PAUSED_FOR_HUMAN:
            escalation = EscalationCompressionEngine.build_escalation(
                step.error_log or "Human intervention required.",
                workflow_id=workflow.id,
                step_id=step.id,
                step_name=step.name,
            )
            return RecoveryRecommendation(
                action=RecoveryAction.MANUAL_ESCALATION,
                confidence=0.86 if not loop_risk else 0.72,
                safety_validated=True,
                reason="A human boundary is required before deterministic execution can continue.",
                replay_scope="manual_resume",
                observability_hooks=("escalation_created", "recovery_recommended"),
                escalation=escalation,
            )

        if loop_risk:
            escalation = EscalationCompressionEngine.build_escalation(
                step.error_log or "Replay loop risk detected.",
                workflow_id=workflow.id,
                step_id=step.id,
                step_name=step.name,
                context={"attempts": attempts},
            )
            return RecoveryRecommendation(
                action=RecoveryAction.MANUAL_ESCALATION,
                confidence=0.68,
                safety_validated=True,
                reason="Repeated attempts indicate replay loop risk.",
                replay_scope="manual_review",
                observability_hooks=("replay_loop_detected", "escalation_created"),
                escalation=escalation,
            )

        if any(pattern in error for pattern in cls.ATS_DRIFT_PATTERNS):
            return RecoveryRecommendation(
                action=RecoveryAction.REPLAY_CHECKPOINT if safety else RecoveryAction.MANUAL_ESCALATION,
                confidence=0.74 if safety else 0.61,
                safety_validated=safety,
                reason="ATS drift is suspected; replay is allowed only if prior checkpoints are durable.",
                replay_scope="failed_checkpoint" if safety else "manual_review",
                observability_hooks=("selector_health", "recovery_recommended"),
            )

        if any(pattern in error for pattern in cls.TRANSIENT_PATTERNS):
            return RecoveryRecommendation(
                action=RecoveryAction.REPLAY_NODE if safety else RecoveryAction.REPLAY_CHECKPOINT,
                confidence=0.88 if safety else 0.76,
                safety_validated=safety,
                reason="Failure looks transient and the shortest safe path is replay.",
                replay_scope="current_node" if safety else "checkpoint",
                observability_hooks=("replay_safety_validation", "recovery_recommended"),
            )

        return RecoveryRecommendation(
            action=RecoveryAction.REPLAY_CHECKPOINT if safety else RecoveryAction.MANUAL_ESCALATION,
            confidence=0.78 if safety else 0.64,
            safety_validated=safety,
            reason="Generic failure mapped to checkpoint replay with safety validation.",
            replay_scope="failed_checkpoint" if safety else "manual_review",
            observability_hooks=("replay_safety_validation", "recovery_recommended"),
        )

    @staticmethod
    def validate_replay_safety(step: WorkflowStep, workflow_steps: list[WorkflowStep]) -> bool:
        if step.status == WorkflowStatus.COMPLETED:
            return False
        if step.name == "SUBMIT_APPLICATION":
            return False
        previous_steps = [
            previous
            for previous in workflow_steps
            if previous.id < step.id
        ]
        return all(previous.status == WorkflowStatus.COMPLETED for previous in previous_steps)

    @classmethod
    def summarize_paths(
        cls,
        workflows: list[ApplicationWorkflow],
        steps_by_workflow: dict[int, list[WorkflowStep]],
    ) -> dict[str, Any]:
        recommendations = []
        for workflow in workflows:
            for step in steps_by_workflow.get(workflow.id, []):
                if step.status not in [WorkflowStatus.FAILED, WorkflowStatus.PAUSED_FOR_HUMAN]:
                    continue
                recommendations.append(
                    cls.recommend(workflow, step, steps_by_workflow.get(workflow.id, [])).to_dict()
                )

        action_counts: dict[str, int] = {}
        for recommendation in recommendations:
            action = recommendation["action"]
            action_counts[action] = action_counts.get(action, 0) + 1

        return {
            "available_actions": [action.value for action in RecoveryAction],
            "recommendations": recommendations[:12],
            "action_distribution": [
                {"action": action, "count": count}
                for action, count in sorted(action_counts.items())
            ],
            "mean_confidence": round(
                sum(item["confidence"] for item in recommendations) / len(recommendations),
                2,
            ) if recommendations else 0,
            "safety_validated": len([item for item in recommendations if item["safety_validated"]]),
        }
