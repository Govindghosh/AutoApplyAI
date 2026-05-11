from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.event import SystemEvent
from app.models.personalization import (
    ExplainabilityLevel,
    OrchestrationTrustMode,
    OrchestrationTrustProfile,
    RecoveryGuidanceMode,
    TrustCalibrationEvent,
)
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.services.event_service import EventType


class OrchestrationPersonalizationService:
    """
    Personalizes orchestration collaboration behavior while keeping workflow
    execution deterministic and governed.
    """

    IMMUTABLE_GOVERNANCE = {
        "mandatory_final_approval": True,
        "completed_checkpoint_replay_blocked": True,
        "submit_application_auto_replay": False,
        "replay_requires_safety_validation": True,
        "policy_mutation_requires_governance_review": True,
    }

    MODE_DEFAULTS: dict[str, dict[str, Any]] = {
        OrchestrationTrustMode.CONSERVATIVE.value: {
            "supervision_intensity": "high",
            "approval_posture": "show_more_review_points",
            "replay_confirmation": "confirm_each_replay",
            "replay_suggestion_threshold": 0.88,
            "max_replay_suggestions_per_workflow": 1,
        },
        OrchestrationTrustMode.BALANCED.value: {
            "supervision_intensity": "standard",
            "approval_posture": "standard_governance_boundaries",
            "replay_confirmation": "confirm_replay_when_confidence_is_directional",
            "replay_suggestion_threshold": 0.78,
            "max_replay_suggestions_per_workflow": 2,
        },
        OrchestrationTrustMode.AGGRESSIVE.value: {
            "supervision_intensity": "low",
            "approval_posture": "mandatory_boundaries_only",
            "replay_confirmation": "compress_replay_confirmation_copy",
            "replay_suggestion_threshold": 0.68,
            "max_replay_suggestions_per_workflow": 3,
        },
    }

    @classmethod
    def get_or_create_profile(cls, db: Session, user_id: int) -> OrchestrationTrustProfile:
        profile = db.query(OrchestrationTrustProfile).filter(
            OrchestrationTrustProfile.user_id == user_id
        ).first()
        if profile:
            return profile

        profile = OrchestrationTrustProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @classmethod
    def update_profile(
        cls,
        db: Session,
        user_id: int,
        values: dict[str, Any],
    ) -> OrchestrationTrustProfile:
        profile = cls.get_or_create_profile(db, user_id)
        allowed = {
            "trust_mode",
            "explainability_level",
            "recovery_guidance_mode",
            "verbose_explainability",
            "minimal_explainability",
            "escalation_batching",
            "grouped_approvals",
            "interruption_sensitivity",
            "replay_auto_suggestions",
            "captcha_handling_preference",
            "max_replay_suggestions_per_workflow",
            "preference_metadata",
        }
        for key, value in values.items():
            if key not in allowed or value is None:
                continue
            setattr(profile, key, value)

        cls._normalize_profile(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @classmethod
    def record_calibration_event(
        cls,
        db: Session,
        user_id: int,
        event_name: str,
        workflow_id: int | None = None,
        step_id: int | None = None,
        latency_ms: int | None = None,
        confidence: float | None = None,
        value: str | None = None,
        metadata: dict[str, Any] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        profile = cls.get_or_create_profile(db, user_id)
        event = TrustCalibrationEvent(
            user_id=user_id,
            workflow_id=workflow_id,
            step_id=step_id,
            event_name=event_name,
            profile_mode=cls._enum_value(profile.trust_mode),
            latency_ms=latency_ms,
            confidence=confidence,
            value=value,
            metadata_json=metadata or {},
            note=note,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return cls.serialize_calibration_event(event)

    @classmethod
    def build_dashboard(cls, db: Session, user_id: int) -> dict[str, Any]:
        profile = cls.get_or_create_profile(db, user_id)
        events = db.query(TrustCalibrationEvent).filter(
            TrustCalibrationEvent.user_id == user_id
        ).all()
        system_events = db.query(SystemEvent).filter(SystemEvent.user_id == user_id).all()
        workflows = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.user_id == user_id).all()
        steps = db.query(WorkflowStep).join(ApplicationWorkflow).filter(
            ApplicationWorkflow.user_id == user_id
        ).all()

        event_counts = Counter(event.event_name for event in events)
        approval_events = [event for event in events if event.event_name == "approval_hesitation"]
        replay_accepts = event_counts["replay_accepted"]
        replay_avoids = event_counts["replay_avoidance"]
        replay_total = replay_accepts + replay_avoids
        escalations = [step for step in steps if step.status == WorkflowStatus.PAUSED_FOR_HUMAN]

        product_events = [
            event for event in system_events
            if event.event_type == EventType.PRODUCT_TELEMETRY.value
        ]
        explanation_views = len([
            event for event in product_events
            if (event.payload or {}).get("event_type") in [
                "workflow_supervisor_opened",
                "explanation_layer_changed",
            ]
        ])

        return {
            "profile": cls.serialize_profile(profile),
            "effective_policy": cls.effective_policy(profile),
            "analytics": {
                "approval_hesitation": {
                    "events": len(approval_events),
                    "mean_latency_ms": cls._avg([event.latency_ms for event in approval_events]),
                },
                "replay_confidence_rate": round((replay_accepts / replay_total * 100), 2) if replay_total else 0,
                "replay_avoidance": replay_avoids,
                "escalation_abandonment": event_counts["escalation_abandonment"],
                "termination_hesitation": event_counts["termination_hesitation"],
                "override_frequency": event_counts["override_frequency"],
                "escalation_fatigue_rate": round(
                    (len(escalations) / max(len(workflows), 1)) * 100,
                    2,
                ) if workflows else 0,
                "explainability_engagement": {
                    "views": explanation_views,
                    "trace_exports": len([
                        event for event in system_events
                        if event.event_type == EventType.WORKFLOW_TRACE_EXPORTED.value
                    ]),
                },
                "approval_latency_by_profile": {
                    cls._enum_value(profile.trust_mode): cls._avg([event.latency_ms for event in approval_events]),
                },
            },
            "recent_calibration_events": [
                cls.serialize_calibration_event(event)
                for event in sorted(events, key=lambda item: cls._sort_timestamp(item.created_at), reverse=True)[:12]
            ],
            "guardrails": {
                "note": "Preferences personalize collaboration behavior only; node order, checkpoint safety, and final approval semantics remain deterministic.",
                "immutable_safeguards": cls.IMMUTABLE_GOVERNANCE,
            },
        }

    @classmethod
    def effective_policy(cls, profile: OrchestrationTrustProfile) -> dict[str, Any]:
        mode = cls._enum_value(profile.trust_mode)
        defaults = cls.MODE_DEFAULTS.get(mode, cls.MODE_DEFAULTS[OrchestrationTrustMode.BALANCED.value])
        suggestion_cap = profile.max_replay_suggestions_per_workflow or defaults["max_replay_suggestions_per_workflow"]
        suggestion_cap = max(0, min(suggestion_cap, defaults["max_replay_suggestions_per_workflow"]))

        return {
            **defaults,
            "trust_mode": mode,
            "explainability_level": cls._enum_value(profile.explainability_level),
            "recovery_guidance_mode": cls._enum_value(profile.recovery_guidance_mode),
            "escalation_batching": bool(profile.escalation_batching),
            "grouped_approvals": bool(profile.grouped_approvals),
            "interruption_sensitivity": profile.interruption_sensitivity or "normal",
            "captcha_handling_preference": profile.captcha_handling_preference or "pause_with_guidance",
            "replay_auto_suggestions": bool(profile.replay_auto_suggestions),
            "max_replay_suggestions_per_workflow": suggestion_cap,
            "automation_boundary": "preferences_do_not_mutate_workflow_execution",
            "immutable_governance": cls.IMMUTABLE_GOVERNANCE,
        }

    @classmethod
    def compress_workflow_summary(
        cls,
        summary: dict[str, Any],
        workflow: ApplicationWorkflow,
        steps: list[WorkflowStep],
        profile: OrchestrationTrustProfile,
    ) -> dict[str, Any]:
        level = cls._explainability_level(profile)
        policy = cls.effective_policy(profile)

        if level == ExplainabilityLevel.BASIC.value:
            return {
                "headline": summary["headline"],
                "status_text": summary["status_text"],
                "completed_steps": summary["completed_steps"],
                "total_steps": summary["total_steps"],
                "progress_percent": summary["progress_percent"],
                "next_action_summary": cls._next_action_summary(steps, profile),
                "explainability_level": level,
                "personalization": {
                    "trust_mode": cls._enum_value(profile.trust_mode),
                    "supervision_intensity": policy["supervision_intensity"],
                },
            }

        enriched = {
            **summary,
            "explainability_level": level,
            "personalization": {
                "trust_mode": cls._enum_value(profile.trust_mode),
                "supervision_intensity": policy["supervision_intensity"],
                "escalation_batching": policy["escalation_batching"],
                "grouped_approvals": policy["grouped_approvals"],
            },
        }
        if level == ExplainabilityLevel.OPERATIONAL.value:
            enriched["operational_semantics"] = {
                "workflow_id": workflow.id,
                "job_id": workflow.job_id,
                "platform": workflow.platform_type or "Generic",
                "checkpoint_policy": "completed checkpoints are durable and replay resumes from incomplete nodes",
                "final_submit_policy": "mandatory explicit approval",
            }
        return enriched

    @classmethod
    def compress_step_explanation(
        cls,
        explanation: dict[str, Any],
        step: WorkflowStep,
        workflow: ApplicationWorkflow,
        profile: OrchestrationTrustProfile,
    ) -> dict[str, Any]:
        level = cls._explainability_level(profile)
        output_data = step.output_data or {}
        recovery = output_data.get("recovery_recommendation")
        if recovery:
            explanation["personalized_recovery_guidance"] = cls.personalize_recovery_guidance(
                workflow,
                step,
                recovery,
                profile,
            )

        escalation = explanation.get("escalation")
        if escalation:
            explanation["personalized_escalation"] = cls.personalize_escalation(escalation, profile)

        if level == ExplainabilityLevel.BASIC.value:
            return {
                "label": explanation["label"],
                "status_text": explanation["status_text"],
                "summary": explanation["summary"],
                "why": explanation["why"],
                "recovery_hint": explanation.get("personalized_recovery_guidance", {}).get("message")
                or explanation.get("recovery_hint"),
                "next_action": explanation["next_action"],
                "risk_level": explanation["risk_level"],
                "explainability_level": level,
            }

        explanation["explainability_level"] = level
        if level != ExplainabilityLevel.OPERATIONAL.value:
            explanation.pop("primitive", None)
        return explanation

    @classmethod
    def personalize_escalation(
        cls,
        escalation: dict[str, Any],
        profile: OrchestrationTrustProfile,
    ) -> dict[str, Any]:
        policy = cls.effective_policy(profile)
        interrupt_now = True
        if policy["interruption_sensitivity"] == "low" and escalation.get("priority") != "high":
            interrupt_now = False
        if policy["captcha_handling_preference"] == "immediate_interrupt" and escalation.get("category") == "captcha_or_identity":
            interrupt_now = True

        return {
            "presentation": "batched" if policy["escalation_batching"] and not interrupt_now else "immediate",
            "grouped_approval_eligible": bool(policy["grouped_approvals"]) and escalation.get("governance_boundary") != "final_submission",
            "interruption": "interrupt_now" if interrupt_now else "defer_to_batch",
            "copy_density": "minimal" if profile.minimal_explainability else "verbose" if profile.verbose_explainability else "standard",
            "governance_boundary": escalation.get("governance_boundary"),
            "mutation_allowed": False,
        }

    @classmethod
    def personalize_recovery_guidance(
        cls,
        workflow: ApplicationWorkflow,
        step: WorkflowStep,
        recovery: dict[str, Any],
        profile: OrchestrationTrustProfile,
    ) -> dict[str, Any]:
        mode = cls._enum_value(profile.recovery_guidance_mode)
        confidence = recovery.get("confidence", 0)
        checkpoint = workflow.current_step_index or 0
        error = (step.error_log or recovery.get("reason") or "").lower()

        if mode == RecoveryGuidanceMode.ADVANCED.value:
            message = (
                f"Workflow paused at {step.name} node. "
                f"Recovery action: {recovery.get('action')}. "
                f"Replay scope: {recovery.get('replay_scope')}. "
                f"Checkpoint {checkpoint} safety validated: {recovery.get('safety_validated')}."
            )
        elif "captcha" in error or "verification" in error:
            message = (
                "Your application paused because the site requested verification. "
                "Completed checkpoints are preserved. Resume the workflow after verification."
            )
        else:
            message = (
                "The workflow paused before continuing. "
                "Completed steps are preserved, and the recommended recovery path is shown below."
            )

        return {
            "mode": mode,
            "message": message,
            "confidence_label": cls._confidence_label(confidence),
            "safe_to_suggest_replay": bool(
                profile.replay_auto_suggestions
                and recovery.get("safety_validated")
                and recovery.get("action") in ["replay_node", "replay_checkpoint"]
            ),
            "mutation_allowed": False,
        }

    @classmethod
    def serialize_profile(cls, profile: OrchestrationTrustProfile) -> dict[str, Any]:
        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "trust_mode": cls._enum_value(profile.trust_mode),
            "explainability_level": cls._enum_value(profile.explainability_level),
            "recovery_guidance_mode": cls._enum_value(profile.recovery_guidance_mode),
            "verbose_explainability": bool(profile.verbose_explainability),
            "minimal_explainability": bool(profile.minimal_explainability),
            "escalation_batching": bool(profile.escalation_batching),
            "grouped_approvals": bool(profile.grouped_approvals),
            "interruption_sensitivity": profile.interruption_sensitivity,
            "replay_auto_suggestions": bool(profile.replay_auto_suggestions),
            "captcha_handling_preference": profile.captcha_handling_preference,
            "max_replay_suggestions_per_workflow": profile.max_replay_suggestions_per_workflow,
            "preference_metadata": profile.preference_metadata or {},
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }

    @staticmethod
    def serialize_calibration_event(event: TrustCalibrationEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "workflow_id": event.workflow_id,
            "step_id": event.step_id,
            "event_name": event.event_name,
            "profile_mode": event.profile_mode,
            "latency_ms": event.latency_ms,
            "confidence": event.confidence,
            "value": event.value,
            "metadata": event.metadata_json or {},
            "note": event.note,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }

    @classmethod
    def _normalize_profile(cls, profile: OrchestrationTrustProfile) -> None:
        if profile.verbose_explainability:
            profile.minimal_explainability = False
            profile.explainability_level = ExplainabilityLevel.OPERATIONAL
        if profile.minimal_explainability:
            profile.verbose_explainability = False
            profile.explainability_level = ExplainabilityLevel.BASIC

        mode = cls._enum_value(profile.trust_mode)
        cap = cls.MODE_DEFAULTS.get(mode, cls.MODE_DEFAULTS[OrchestrationTrustMode.BALANCED.value])[
            "max_replay_suggestions_per_workflow"
        ]
        requested = profile.max_replay_suggestions_per_workflow or cap
        profile.max_replay_suggestions_per_workflow = max(0, min(requested, cap))

    @classmethod
    def _explainability_level(cls, profile: OrchestrationTrustProfile) -> str:
        if profile.minimal_explainability:
            return ExplainabilityLevel.BASIC.value
        if profile.verbose_explainability:
            return ExplainabilityLevel.OPERATIONAL.value
        return cls._enum_value(profile.explainability_level)

    @classmethod
    def _next_action_summary(cls, steps: list[WorkflowStep], profile: OrchestrationTrustProfile) -> str:
        active = next(
            (
                step for step in steps
                if step.status in [WorkflowStatus.FAILED, WorkflowStatus.PAUSED_FOR_HUMAN, WorkflowStatus.RUNNING]
            ),
            None,
        )
        if not active:
            return "No immediate action is needed."
        if active.status == WorkflowStatus.PAUSED_FOR_HUMAN:
            return "Review the paused checkpoint when you are ready."
        if active.status == WorkflowStatus.FAILED:
            return "Review the recovery recommendation before replaying."
        return "Workflow is running."

    @staticmethod
    def _confidence_label(confidence: float | int | None) -> str:
        confidence = confidence or 0
        if confidence >= 0.85:
            return "high"
        if confidence >= 0.7:
            return "medium"
        return "low"

    @staticmethod
    def _avg(values: list[int | None]) -> float:
        clean = [value for value in values if value is not None]
        return round(sum(clean) / len(clean), 2) if clean else 0

    @staticmethod
    def _sort_timestamp(value: datetime | None) -> float:
        if not value:
            return 0.0
        if value.tzinfo:
            return value.timestamp()
        return value.replace(tzinfo=timezone.utc).timestamp()

    @staticmethod
    def _enum_value(value: Any) -> str:
        return value.value if hasattr(value, "value") else str(value)
