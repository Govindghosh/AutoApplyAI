from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class EscalationTemplateName(str, Enum):
    HUMAN_INPUT_REQUIRED = "human_input_required"
    VERIFICATION_REQUIRED = "verification_required"
    MANUAL_RESUME_REQUIRED = "manual_resume_required"
    APPROVAL_REQUIRED = "approval_required"
    ATS_FAILURE = "ats_failure"
    REPLAY_INTERVENTION = "replay_intervention"


@dataclass(frozen=True)
class EscalationTemplate:
    name: EscalationTemplateName
    title: str
    category: str
    default_priority: str
    expected_resolution: str
    fatigue_weight: float
    governance_boundary: str
    allowed_actions: tuple[str, ...]
    description: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["name"] = self.name.value
        return data


class EscalationCompressionEngine:
    """
    Reduces fragmented human intervention paths into stable templates.
    """

    TEMPLATES: dict[EscalationTemplateName, EscalationTemplate] = {
        EscalationTemplateName.HUMAN_INPUT_REQUIRED: EscalationTemplate(
            name=EscalationTemplateName.HUMAN_INPUT_REQUIRED,
            title="Human input required",
            category="unknown_field",
            default_priority="medium",
            expected_resolution="Provide missing field value or mark field as skipped.",
            fatigue_weight=1.0,
            governance_boundary="human_supplied_data",
            allowed_actions=("resolve_step", "skip_optional_field", "terminate_safely"),
            description="A workflow field cannot be completed from approved profile or resume data.",
        ),
        EscalationTemplateName.VERIFICATION_REQUIRED: EscalationTemplate(
            name=EscalationTemplateName.VERIFICATION_REQUIRED,
            title="Verification required",
            category="captcha_or_identity",
            default_priority="high",
            expected_resolution="Complete site verification in the active browser session.",
            fatigue_weight=1.4,
            governance_boundary="identity_or_captcha",
            allowed_actions=("resolve_step", "replay_checkpoint", "terminate_safely"),
            description="The ATS introduced a captcha, login, or identity checkpoint.",
        ),
        EscalationTemplateName.MANUAL_RESUME_REQUIRED: EscalationTemplate(
            name=EscalationTemplateName.MANUAL_RESUME_REQUIRED,
            title="Manual resume action required",
            category="resume_upload",
            default_priority="high",
            expected_resolution="Confirm file availability or upload the resume manually.",
            fatigue_weight=1.2,
            governance_boundary="resume_artifact",
            allowed_actions=("resolve_step", "replay_checkpoint", "terminate_safely"),
            description="Resume upload could not be completed safely by automation.",
        ),
        EscalationTemplateName.APPROVAL_REQUIRED: EscalationTemplate(
            name=EscalationTemplateName.APPROVAL_REQUIRED,
            title="Approval required",
            category="approval_gate",
            default_priority="medium",
            expected_resolution="Review the prepared application and approve submission.",
            fatigue_weight=0.8,
            governance_boundary="final_submission",
            allowed_actions=("approve", "request_changes", "terminate_safely"),
            description="Workflow reached a deliberate governance checkpoint.",
        ),
        EscalationTemplateName.ATS_FAILURE: EscalationTemplate(
            name=EscalationTemplateName.ATS_FAILURE,
            title="ATS failure",
            category="platform_or_selector_drift",
            default_priority="high",
            expected_resolution="Inspect ATS state, then replay or switch to manual path.",
            fatigue_weight=1.5,
            governance_boundary="operator_review",
            allowed_actions=("replay_checkpoint", "escalate_to_support", "terminate_safely"),
            description="The target ATS appears unstable, changed, or unavailable.",
        ),
        EscalationTemplateName.REPLAY_INTERVENTION: EscalationTemplate(
            name=EscalationTemplateName.REPLAY_INTERVENTION,
            title="Replay intervention",
            category="recovery_loop",
            default_priority="medium",
            expected_resolution="Choose replay checkpoint, manual continuation, or safe termination.",
            fatigue_weight=1.3,
            governance_boundary="recovery_decision",
            allowed_actions=("replay_node", "replay_checkpoint", "manual_resume", "terminate_safely"),
            description="Recovery confidence is too low for an automatic retry.",
        ),
    }

    @classmethod
    def template_for_reason(cls, reason: str, step_name: str | None = None) -> EscalationTemplate:
        reason_lower = (reason or "").lower()
        step_lower = (step_name or "").lower()

        if "captcha" in reason_lower or "verification" in reason_lower or "login" in reason_lower or "auth" in reason_lower:
            return cls.TEMPLATES[EscalationTemplateName.VERIFICATION_REQUIRED]
        if "resume" in reason_lower or "upload" in reason_lower or "file" in reason_lower or "upload" in step_lower:
            return cls.TEMPLATES[EscalationTemplateName.MANUAL_RESUME_REQUIRED]
        if "approval" in reason_lower or "submit" in step_lower:
            return cls.TEMPLATES[EscalationTemplateName.APPROVAL_REQUIRED]
        if "selector" in reason_lower or "ats" in reason_lower or "element" in reason_lower:
            return cls.TEMPLATES[EscalationTemplateName.ATS_FAILURE]
        if "replay" in reason_lower or "retry" in reason_lower:
            return cls.TEMPLATES[EscalationTemplateName.REPLAY_INTERVENTION]
        return cls.TEMPLATES[EscalationTemplateName.HUMAN_INPUT_REQUIRED]

    @classmethod
    def build_escalation(
        cls,
        reason: str,
        workflow_id: int | None = None,
        step_id: int | None = None,
        step_name: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        template = cls.template_for_reason(reason, step_name)
        return {
            "template": template.name.value,
            "title": template.title,
            "category": template.category,
            "priority": template.default_priority,
            "expected_resolution": template.expected_resolution,
            "fatigue_weight": template.fatigue_weight,
            "governance_boundary": template.governance_boundary,
            "allowed_actions": list(template.allowed_actions),
            "reason": reason,
            "workflow_id": workflow_id,
            "step_id": step_id,
            "step_name": step_name,
            "context": context or {},
            "mutation_allowed": False,
        }

    @classmethod
    def catalog(cls) -> list[dict[str, Any]]:
        return [template.to_dict() for template in cls.TEMPLATES.values()]
