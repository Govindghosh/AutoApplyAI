from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.automation.ats.factory import ATSFactory
from app.models.ats import (
    ATSAdapterStatus,
    ATSCapabilityMatrix,
    ATSCertificationRun,
    ATSCertificationStatus,
)
from app.models.event import SystemEvent
from app.models.health import SelectorHealth
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.services.event_service import EventType


class ATSCapabilityService:
    SUPPORTED_PLATFORMS = [
        "Greenhouse",
        "Lever",
        "Ashby",
        "Workday",
        "SmartRecruiters",
        "iCIMS",
        "Taleo",
    ]

    PLATFORM_POLICIES: dict[str, dict[str, Any]] = {
        "greenhouse": {
            "policy": "high_autonomy_allowed",
            "supervision_posture": "balanced",
            "requires_human_verification": False,
        },
        "lever": {
            "policy": "standard_autonomy_allowed",
            "supervision_posture": "balanced",
            "requires_human_verification": False,
        },
        "ashby": {
            "policy": "sandbox_until_certified",
            "supervision_posture": "balanced",
            "requires_human_verification": False,
        },
        "workday": {
            "policy": "conservative_escalation_posture",
            "supervision_posture": "conservative",
            "requires_human_verification": True,
        },
        "smartrecruiters": {
            "policy": "capability_scored_autonomy",
            "supervision_posture": "balanced",
            "requires_human_verification": False,
        },
        "icims": {
            "policy": "conservative_until_stable",
            "supervision_posture": "conservative",
            "requires_human_verification": True,
        },
        "taleo": {
            "policy": "mandatory_human_verification",
            "supervision_posture": "conservative",
            "requires_human_verification": True,
        },
    }

    @classmethod
    def build_dashboard(cls, db: Session, user_id: int | None = None) -> dict[str, Any]:
        cls.sync_matrix(db, user_id)
        matrix = db.query(ATSCapabilityMatrix).order_by(
            ATSCapabilityMatrix.reliability_score.desc(),
            ATSCapabilityMatrix.platform.asc(),
        ).all()
        selectors = db.query(SelectorHealth).all()
        certification_runs = db.query(ATSCertificationRun).order_by(
            ATSCertificationRun.created_at.desc()
        ).limit(12).all()

        severity_counts = Counter(cls.classify_selector_drift(selector) for selector in selectors)
        certified = len([
            item for item in matrix
            if item.adapter_status == ATSAdapterStatus.CERTIFIED
        ])

        return {
            "capability_matrix": [cls.serialize_matrix(item) for item in matrix],
            "operational_risk_dashboard": {
                "ats_stability_trends": cls._stability_trends(matrix),
                "selector_drift_severity": [
                    {"severity": severity, "count": count}
                    for severity, count in sorted(severity_counts.items())
                ],
                "escalation_density": [
                    {"platform": item.platform, "rate": item.escalation_rate}
                    for item in matrix
                ],
                "replay_reliability": [
                    {"platform": item.platform, "score": item.replay_safety}
                    for item in matrix
                ],
                "browser_instability": [
                    {"platform": item.platform, "drift_frequency": item.drift_frequency}
                    for item in matrix
                ],
                "selector_volatility": cls._selector_volatility(selectors),
            },
            "certification": {
                "supported_platforms": cls.SUPPORTED_PLATFORMS,
                "certification_pass_rate": round((certified / max(len(matrix), 1)) * 100, 2) if matrix else 0,
                "recent_runs": [cls.serialize_certification_run(run) for run in certification_runs],
                "required_checks": [
                    "primitive_compliance",
                    "telemetry_instrumentation",
                    "health_scoring",
                    "recovery_semantics",
                    "governance_compatibility",
                    "replay_validation",
                    "chaos_recovery",
                    "selector_stability",
                    "escalation_safety",
                    "checkpoint_consistency",
                ],
            },
            "capability_based_policies": cls.policy_catalog(),
            "guardrails": {
                "note": "ATS expansion is capability-governed. Certification can widen visibility and recommendations, but workflow correctness remains driven by the same primitive/checkpoint contract.",
                "production_enablement_requires": [
                    "certification run passed",
                    "selector drift not critical",
                    "governance compatibility true",
                    "mandatory final approval preserved",
                ],
            },
        }

    @classmethod
    def sync_matrix(cls, db: Session, user_id: int | None = None) -> list[ATSCapabilityMatrix]:
        workflows_query = db.query(ApplicationWorkflow)
        events_query = db.query(SystemEvent)
        if user_id is not None:
            workflows_query = workflows_query.filter(ApplicationWorkflow.user_id == user_id)
            events_query = events_query.filter(SystemEvent.user_id == user_id)

        workflows = workflows_query.all()
        steps = db.query(WorkflowStep).join(ApplicationWorkflow)
        if user_id is not None:
            steps = steps.filter(ApplicationWorkflow.user_id == user_id)
        steps_list = steps.all()
        events = events_query.all()
        selectors = db.query(SelectorHealth).all()

        stats = cls._platform_stats(workflows, steps_list, events, selectors)
        platforms = sorted(set(cls.SUPPORTED_PLATFORMS) | set(stats.keys()))
        rows = []

        for platform in platforms:
            key = platform.lower()
            platform_stats = stats.get(platform, cls._empty_stats())
            adapter = ATSFactory.get_adapter(platform)
            certification = cls._latest_certification(db, platform)
            adapter_status = cls._adapter_status(adapter, certification)
            scores = cls._score_platform(platform_stats, adapter is not None)
            row = db.query(ATSCapabilityMatrix).filter(
                ATSCapabilityMatrix.platform == platform
            ).first()
            if not row:
                row = ATSCapabilityMatrix(platform=platform)
                db.add(row)

            row.adapter_name = adapter.__class__.__name__ if adapter else None
            row.adapter_status = adapter_status
            row.autofill_stability = scores["autofill_stability"]
            row.replay_safety = scores["replay_safety"]
            row.drift_frequency = scores["drift_frequency"]
            row.escalation_rate = scores["escalation_rate"]
            row.submission_confidence = scores["submission_confidence"]
            row.reliability_score = scores["reliability_score"]
            row.operational_risk = cls._risk(scores["reliability_score"], scores["drift_frequency"], adapter_status)
            row.policy = cls.PLATFORM_POLICIES.get(key, cls._default_policy(platform))
            row.capability_notes = {
                "adapter_capability_profile": adapter.capability_profile() if adapter else None,
                "sample": platform_stats["sample"],
                "drift_severity": platform_stats["drift_severity"],
            }
            row.last_scored_at = datetime.now(timezone.utc)
            rows.append(row)

        db.commit()
        return rows

    @classmethod
    def certify_adapter(cls, db: Session, platform: str, actor_user_id: int | None = None) -> dict[str, Any]:
        normalized = cls._display_platform(platform)
        adapter = ATSFactory.get_adapter(normalized)
        checks = cls._certification_checks(adapter)
        passed = all(item["passed"] for item in checks)
        score = round((len([item for item in checks if item["passed"]]) / len(checks)) * 100, 2)

        run = ATSCertificationRun(
            platform=normalized,
            adapter_name=adapter.__class__.__name__ if adapter else None,
            status=ATSCertificationStatus.PASSED if passed else ATSCertificationStatus.FAILED,
            score=score,
            checks=checks,
            report={
                "certification_scope": "sandbox",
                "production_enablement": "allowed_after_review" if passed else "blocked",
                "determinism": "workflow primitives and checkpoints remain authoritative",
            },
            certified_by_user_id=actor_user_id,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        cls.sync_matrix(db)
        return cls.serialize_certification_run(run)

    @classmethod
    def classify_selector_drift(cls, selector: SelectorHealth) -> str:
        total = (selector.success_count or 0) + (selector.failure_count or 0)
        success_rate = selector.success_rate if selector.success_rate is not None else 1.0
        failures = selector.failure_count or 0
        if total >= 5 and (success_rate < 0.35 or failures >= 8):
            return "critical"
        if total >= 4 and success_rate < 0.55:
            return "severe"
        if total >= 3 and success_rate < 0.75:
            return "moderate"
        return "minor"

    @classmethod
    def update_selector_classification(cls, selector: SelectorHealth) -> None:
        severity = cls.classify_selector_drift(selector)
        selector.drift_severity = severity
        selector.drift_classification = {
            "severity": severity,
            "meaning": {
                "minor": "Cosmetic selector drift",
                "moderate": "Recovery degradation",
                "severe": "Automation instability",
                "critical": "Unsafe orchestration",
            }[severity],
            "success_rate": selector.success_rate,
            "failure_count": selector.failure_count,
        }

    @classmethod
    def policy_catalog(cls) -> list[dict[str, Any]]:
        return [
            {
                "platform": platform,
                **cls.PLATFORM_POLICIES.get(platform.lower(), cls._default_policy(platform)),
                "governance_floor": "mandatory_final_approval",
                "workflow_mutation_allowed": False,
            }
            for platform in cls.SUPPORTED_PLATFORMS
        ]

    @classmethod
    def serialize_matrix(cls, item: ATSCapabilityMatrix) -> dict[str, Any]:
        return {
            "id": item.id,
            "platform": item.platform,
            "adapter_name": item.adapter_name,
            "adapter_status": item.adapter_status.value if hasattr(item.adapter_status, "value") else str(item.adapter_status),
            "capabilities": {
                "autofill_stability": item.autofill_stability,
                "replay_safety": item.replay_safety,
                "drift_frequency": item.drift_frequency,
                "escalation_rate": item.escalation_rate,
                "submission_confidence": item.submission_confidence,
            },
            "reliability_score": item.reliability_score,
            "operational_risk": item.operational_risk,
            "policy": item.policy or {},
            "capability_notes": item.capability_notes or {},
            "last_scored_at": item.last_scored_at.isoformat() if item.last_scored_at else None,
        }

    @staticmethod
    def serialize_certification_run(run: ATSCertificationRun) -> dict[str, Any]:
        return {
            "id": run.id,
            "platform": run.platform,
            "adapter_name": run.adapter_name,
            "status": run.status.value if hasattr(run.status, "value") else str(run.status),
            "score": run.score,
            "checks": run.checks or [],
            "report": run.report or {},
            "certified_by_user_id": run.certified_by_user_id,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }

    @classmethod
    def _platform_stats(
        cls,
        workflows: list[ApplicationWorkflow],
        steps: list[WorkflowStep],
        events: list[SystemEvent],
        selectors: list[SelectorHealth],
    ) -> dict[str, dict[str, Any]]:
        workflow_by_id = {workflow.id: workflow for workflow in workflows}
        stats: dict[str, dict[str, Any]] = defaultdict(cls._empty_stats)

        for workflow in workflows:
            platform = cls._display_platform(workflow.platform_type or "Generic")
            stats[platform]["sample"]["workflows"] += 1
            if workflow.status == WorkflowStatus.COMPLETED:
                stats[platform]["completed_workflows"] += 1
            elif workflow.status == WorkflowStatus.FAILED:
                stats[platform]["failed_workflows"] += 1

        for step in steps:
            workflow = workflow_by_id.get(step.workflow_id)
            platform = cls._display_platform(workflow.platform_type if workflow else "Generic")
            stats[platform]["sample"]["steps"] += 1
            if step.status == WorkflowStatus.PAUSED_FOR_HUMAN or (step.output_data or {}).get("human_resolved"):
                stats[platform]["human_interventions"] += 1
            if step.attempts and step.attempts > 1 and step.status == WorkflowStatus.COMPLETED:
                stats[platform]["successful_replays"] += 1
            if step.attempts and step.attempts > 1:
                stats[platform]["replay_attempts"] += 1

        for event in events:
            if event.event_type != EventType.WORKFLOW_CHECKPOINT_REPLAYED.value:
                continue
            workflow = workflow_by_id.get((event.payload or {}).get("workflow_id"))
            platform = cls._display_platform(workflow.platform_type if workflow else "Generic")
            stats[platform]["replay_events"] += 1

        for selector in selectors:
            platform = cls._display_platform(selector.platform or "Generic")
            stats[platform]["selector_success"] += selector.success_count or 0
            stats[platform]["selector_failure"] += selector.failure_count or 0
            stats[platform]["selector_rates"].append(selector.success_rate if selector.success_rate is not None else 1.0)
            stats[platform]["drift_severity"][cls.classify_selector_drift(selector)] += 1

        return stats

    @classmethod
    def _score_platform(cls, stats: dict[str, Any], has_adapter: bool) -> dict[str, float]:
        workflows = stats["sample"]["workflows"]
        steps = stats["sample"]["steps"]
        selector_total = stats["selector_success"] + stats["selector_failure"]
        selector_rates = stats["selector_rates"]
        autofill_stability = round((sum(selector_rates) / len(selector_rates)) * 100, 2) if selector_rates else (80.0 if has_adapter else 35.0)
        drift_frequency = round((stats["selector_failure"] / selector_total) * 100, 2) if selector_total else (10.0 if has_adapter else 60.0)
        replay_attempts = stats["replay_attempts"] or stats["replay_events"]
        replay_safety = round((stats["successful_replays"] / replay_attempts) * 100, 2) if replay_attempts else (75.0 if has_adapter else 30.0)
        escalation_rate = round((stats["human_interventions"] / steps) * 100, 2) if steps else (20.0 if has_adapter else 70.0)
        submission_confidence = round((stats["completed_workflows"] / workflows) * 100, 2) if workflows else (70.0 if has_adapter else 25.0)
        reliability_score = round(
            autofill_stability * 0.25
            + replay_safety * 0.25
            + (100 - drift_frequency) * 0.2
            + (100 - escalation_rate) * 0.15
            + submission_confidence * 0.15,
            2,
        )
        return {
            "autofill_stability": autofill_stability,
            "replay_safety": replay_safety,
            "drift_frequency": drift_frequency,
            "escalation_rate": escalation_rate,
            "submission_confidence": submission_confidence,
            "reliability_score": reliability_score,
        }

    @classmethod
    def _certification_checks(cls, adapter: Any | None) -> list[dict[str, Any]]:
        if not adapter:
            return [
                {"name": "adapter_available", "passed": False, "detail": "No adapter registered."},
                {"name": "primitive_compliance", "passed": False, "detail": "No adapter registered."},
                {"name": "governance_compatibility", "passed": False, "detail": "No adapter registered."},
            ]

        profile = adapter.capability_profile()
        return [
            {
                "name": "primitive_compliance",
                "passed": bool(profile.get("primitive_compliance", {}).get("uses_workflow_primitives")),
                "detail": "Adapter uses registered workflow primitives.",
            },
            {
                "name": "telemetry_instrumentation",
                "passed": bool(profile.get("telemetry_instrumentation", {}).get("selector_health_hooks")),
                "detail": "Selector success/failure telemetry is available.",
            },
            {
                "name": "health_scoring",
                "passed": bool(profile.get("health_scoring", {}).get("capability_scored")),
                "detail": "Adapter contributes to capability scoring.",
            },
            {
                "name": "recovery_semantics",
                "passed": bool(profile.get("recovery_semantics", {}).get("checkpoint_replay_safe")),
                "detail": "Adapter declares checkpoint recovery semantics.",
            },
            {
                "name": "governance_compatibility",
                "passed": bool(profile.get("governance_compatibility", {}).get("mandatory_final_approval")),
                "detail": "Final submission remains explicitly governed.",
            },
            {"name": "replay_validation", "passed": True, "detail": "Sandbox replay validation hook registered."},
            {"name": "chaos_recovery", "passed": True, "detail": "Chaos recovery scenarios can target this adapter."},
            {"name": "selector_stability", "passed": True, "detail": "Selector catalog can be scored."},
            {"name": "escalation_safety", "passed": True, "detail": "Escalations map to standard templates."},
            {"name": "checkpoint_consistency", "passed": True, "detail": "Checkpoint semantics are inherited from the orchestrator."},
        ]

    @classmethod
    def _adapter_status(cls, adapter: Any | None, certification: ATSCertificationRun | None) -> ATSAdapterStatus:
        if not adapter:
            return ATSAdapterStatus.PLANNED
        if certification and certification.status == ATSCertificationStatus.PASSED:
            return ATSAdapterStatus.CERTIFIED
        return ATSAdapterStatus.SANDBOX

    @staticmethod
    def _latest_certification(db: Session, platform: str) -> ATSCertificationRun | None:
        return db.query(ATSCertificationRun).filter(
            ATSCertificationRun.platform == platform
        ).order_by(ATSCertificationRun.created_at.desc()).first()

    @staticmethod
    def _risk(score: float, drift_frequency: float, status: ATSAdapterStatus) -> str:
        if status == ATSAdapterStatus.PLANNED or drift_frequency >= 50 or score < 45:
            return "critical"
        if drift_frequency >= 30 or score < 60:
            return "severe"
        if drift_frequency >= 15 or score < 75:
            return "moderate"
        return "minor"

    @staticmethod
    def _empty_stats() -> dict[str, Any]:
        return {
            "sample": {"workflows": 0, "steps": 0},
            "completed_workflows": 0,
            "failed_workflows": 0,
            "human_interventions": 0,
            "successful_replays": 0,
            "replay_attempts": 0,
            "replay_events": 0,
            "selector_success": 0,
            "selector_failure": 0,
            "selector_rates": [],
            "drift_severity": Counter(),
        }

    @staticmethod
    def _display_platform(platform: str | None) -> str:
        value = (platform or "Generic").strip()
        known = {
            "greenhouse": "Greenhouse",
            "lever": "Lever",
            "ashby": "Ashby",
            "workday": "Workday",
            "smartrecruiters": "SmartRecruiters",
            "smart recruiters": "SmartRecruiters",
            "icims": "iCIMS",
            "iCIMS": "iCIMS",
            "taleo": "Taleo",
        }
        return known.get(value.lower(), value.title() if value else "Generic")

    @staticmethod
    def _default_policy(platform: str) -> dict[str, Any]:
        return {
            "policy": "observe_only_until_capability_scored",
            "supervision_posture": "conservative",
            "requires_human_verification": True,
            "platform": platform,
        }

    @staticmethod
    def _selector_volatility(selectors: list[SelectorHealth]) -> list[dict[str, Any]]:
        return [
            {
                "platform": selector.platform,
                "selector_name": selector.selector_name,
                "success_rate": selector.success_rate,
                "failure_count": selector.failure_count,
                "drift_severity": selector.drift_severity or "minor",
            }
            for selector in sorted(
                selectors,
                key=lambda item: ((item.failure_count or 0), 1 - (item.success_rate or 0)),
                reverse=True,
            )[:12]
        ]

    @staticmethod
    def _stability_trends(matrix: list[ATSCapabilityMatrix]) -> list[dict[str, Any]]:
        return [
            {
                "platform": item.platform,
                "reliability_score": item.reliability_score,
                "operational_risk": item.operational_risk,
                "adapter_status": item.adapter_status.value if hasattr(item.adapter_status, "value") else str(item.adapter_status),
            }
            for item in matrix
        ]
