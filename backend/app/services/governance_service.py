from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.governance import (
    GovernanceTimelineEntry,
    OperationalRecommendation,
    RecommendationStatus,
)
from app.services.pattern_analysis_service import PatternAnalysisService
from app.services.signal_integrity_service import SignalIntegrityService


class GovernanceService:
    @classmethod
    def build(cls, db: Session, user_id: int) -> dict[str, Any]:
        signal = SignalIntegrityService.build(db, user_id)
        pattern = PatternAnalysisService.build(db, user_id)
        cls.sync_review_queue(db, user_id, signal, pattern)

        recommendations = db.query(OperationalRecommendation).filter(
            OperationalRecommendation.user_id == user_id
        ).order_by(OperationalRecommendation.created_at.desc()).all()
        timeline = db.query(GovernanceTimelineEntry).filter(
            GovernanceTimelineEntry.user_id == user_id
        ).order_by(GovernanceTimelineEntry.created_at.desc()).limit(12).all()

        return {
            "review_queue": [cls.serialize_recommendation(item) for item in recommendations[:8]],
            "timeline": [cls.serialize_timeline(item) for item in timeline],
            "metrics": cls.metrics(recommendations),
            "guardrails": {
                "note": "Review-eligible signals create recommendations, but policy changes require explicit approval and rollback evidence.",
                "approval_required_for": [
                    "threshold_change",
                    "selector_policy_change",
                    "replay_policy_change",
                    "automation_scope_change",
                ],
                "shadow_modes": ["simulated_workflow", "low_risk_cohort", "shadow_execution"],
            },
        }

    @classmethod
    def sync_review_queue(
        cls,
        db: Session,
        user_id: int,
        signal: dict[str, Any] | None = None,
        pattern: dict[str, Any] | None = None,
    ) -> None:
        signal = signal or SignalIntegrityService.build(db, user_id)
        pattern = pattern or PatternAnalysisService.build(db, user_id)

        candidates = cls._candidate_recommendations(signal, pattern)
        for candidate in candidates:
            existing = db.query(OperationalRecommendation).filter(
                OperationalRecommendation.user_id == user_id,
                OperationalRecommendation.source_signal == candidate["source_signal"],
                OperationalRecommendation.status == RecommendationStatus.PENDING_REVIEW,
            ).first()
            if existing:
                existing.explainability = candidate["explainability"]
                existing.shadow_evaluation = candidate["shadow_evaluation"]
                continue

            recommendation = OperationalRecommendation(user_id=user_id, **candidate)
            db.add(recommendation)
            db.flush()
            db.add(GovernanceTimelineEntry(
                user_id=user_id,
                recommendation_id=recommendation.id,
                action="review_opened",
                reason=candidate["rationale"],
                after_state=cls.serialize_recommendation(recommendation),
            ))

        db.commit()

    @classmethod
    def approve(cls, db: Session, recommendation_id: int, user_id: int, note: str | None) -> dict[str, Any]:
        recommendation = cls._owned(db, recommendation_id, user_id)
        before = cls.serialize_recommendation(recommendation)
        recommendation.status = RecommendationStatus.APPROVED
        recommendation.reviewer_id = user_id
        recommendation.decision_note = note
        recommendation.approved_at = datetime.now(timezone.utc)
        recommendation.implemented_at = recommendation.approved_at
        db.flush()
        cls._timeline(db, recommendation, user_id, "approved", note, before)
        db.commit()
        return cls.serialize_recommendation(recommendation)

    @classmethod
    def reject(cls, db: Session, recommendation_id: int, user_id: int, note: str | None) -> dict[str, Any]:
        recommendation = cls._owned(db, recommendation_id, user_id)
        before = cls.serialize_recommendation(recommendation)
        recommendation.status = RecommendationStatus.REJECTED
        recommendation.reviewer_id = user_id
        recommendation.decision_note = note
        db.flush()
        cls._timeline(db, recommendation, user_id, "rejected", note, before)
        db.commit()
        return cls.serialize_recommendation(recommendation)

    @classmethod
    def rollback(cls, db: Session, recommendation_id: int, user_id: int, note: str | None) -> dict[str, Any]:
        recommendation = cls._owned(db, recommendation_id, user_id)
        if recommendation.status != RecommendationStatus.APPROVED:
            raise HTTPException(status_code=400, detail="Only approved policy changes can be rolled back")

        before = cls.serialize_recommendation(recommendation)
        recommendation.status = RecommendationStatus.ROLLED_BACK
        recommendation.rolled_back_at = datetime.now(timezone.utc)
        recommendation.decision_note = note or recommendation.decision_note
        db.flush()
        cls._timeline(db, recommendation, user_id, "rolled_back", note, before)
        db.commit()
        return cls.serialize_recommendation(recommendation)

    @classmethod
    def _candidate_recommendations(cls, signal: dict[str, Any], pattern: dict[str, Any]) -> list[dict[str, Any]]:
        if signal["summary"]["optimization_readiness"] not in ["review_eligible", "human_review_only"]:
            return []

        candidates: list[dict[str, Any]] = []
        top_node = (pattern.get("node_patterns") or [None])[0]
        top_platform = (pattern.get("ats_friction") or [None])[0]
        explainability = cls._explainability(signal)

        if top_node and top_node["friction_score"] > 0:
            candidates.append({
                "source_signal": f"node_friction:{top_node['step_name']}",
                "recommendation_type": "replay_policy_change",
                "title": f"Review recovery policy for {top_node['step_name'].replace('_', ' ').title()}",
                "rationale": top_node["recommended_review"],
                "target_policy": f"workflow.node.{top_node['step_name'].lower()}.recovery",
                "proposed_change": {
                    "action": "tighten_human_review_or_replay_guidance",
                    "friction_score": top_node["friction_score"],
                    "observations": top_node["observations"],
                },
                "rollback_plan": {
                    "restore_previous_policy": True,
                    "stop_condition": "rollback if replay success decreases or human override frequency increases",
                },
                "explainability": explainability,
                "shadow_evaluation": cls._shadow_evaluation(signal, top_node),
            })

        if top_platform and top_platform["friction_score"] >= 20:
            candidates.append({
                "source_signal": f"ats_friction:{top_platform['platform']}",
                "recommendation_type": "threshold_change",
                "title": f"Review orchestration thresholds for {top_platform['platform']}",
                "rationale": "ATS friction is high enough for human review before any threshold adjustment.",
                "target_policy": f"ats.{top_platform['platform'].lower()}.escalation_threshold",
                "proposed_change": {
                    "action": "increase_escalation_sensitivity",
                    "friction_score": top_platform["friction_score"],
                    "completion_rate": top_platform["completion_rate"],
                },
                "rollback_plan": {
                    "restore_previous_threshold": True,
                    "stop_condition": "rollback if completion rate drops or stale interventions rise",
                },
                "explainability": explainability,
                "shadow_evaluation": cls._shadow_evaluation(signal, top_platform),
            })

        return candidates

    @staticmethod
    def _explainability(signal: dict[str, Any]) -> dict[str, Any]:
        return {
            "confidence_level": signal["summary"]["overall_confidence"],
            "sample_size": {
                "workflows": signal["sample_quality"]["workflows"],
                "steps": signal["sample_quality"]["steps"],
                "events": signal["sample_quality"]["events"],
            },
            "temporal_stability": signal["summary"]["temporal_stability"],
            "confounder_warnings": signal["causation_guards"],
            "user_segment_scope": signal["segment_analysis"],
            "decay_weight": signal["signal_decay"],
        }

    @staticmethod
    def _shadow_evaluation(signal: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
        return {
            "required_before_rollout": True,
            "mode": "shadow_execution",
            "cohort": "low_risk_workflows",
            "minimum_shadow_samples": max(10, signal["sample_quality"]["workflows"]),
            "candidate_target": target,
            "success_criteria": [
                "no increase in failed workflow rate",
                "no increase in rollback or override frequency",
                "replay success remains at or above current baseline",
            ],
        }

    @staticmethod
    def metrics(recommendations: list[OperationalRecommendation]) -> dict[str, Any]:
        total_decided = len([item for item in recommendations if item.status in [
            RecommendationStatus.APPROVED,
            RecommendationStatus.REJECTED,
            RecommendationStatus.ROLLED_BACK,
        ]])
        approved = len([item for item in recommendations if item.status == RecommendationStatus.APPROVED])
        rolled_back = len([item for item in recommendations if item.status == RecommendationStatus.ROLLED_BACK])
        rejected = len([item for item in recommendations if item.status == RecommendationStatus.REJECTED])
        pending = len([item for item in recommendations if item.status == RecommendationStatus.PENDING_REVIEW])

        return {
            "recommendation_acceptance_rate": round((approved / total_decided * 100), 2) if total_decided else 0,
            "rollback_frequency": rolled_back,
            "policy_drift_rate": approved + rolled_back,
            "false_recommendation_rate": round((rejected / total_decided * 100), 2) if total_decided else 0,
            "human_override_frequency": rejected + rolled_back,
            "pending_reviews": pending,
        }

    @staticmethod
    def serialize_recommendation(item: OperationalRecommendation) -> dict[str, Any]:
        return {
            "id": item.id,
            "source_signal": item.source_signal,
            "recommendation_type": item.recommendation_type,
            "title": item.title,
            "rationale": item.rationale,
            "target_policy": item.target_policy,
            "proposed_change": item.proposed_change or {},
            "rollback_plan": item.rollback_plan or {},
            "explainability": item.explainability or {},
            "shadow_evaluation": item.shadow_evaluation or {},
            "status": item.status.value if hasattr(item.status, "value") else str(item.status),
            "reviewer_id": item.reviewer_id,
            "decision_note": item.decision_note,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "approved_at": item.approved_at.isoformat() if item.approved_at else None,
            "rolled_back_at": item.rolled_back_at.isoformat() if item.rolled_back_at else None,
        }

    @staticmethod
    def serialize_timeline(item: GovernanceTimelineEntry) -> dict[str, Any]:
        return {
            "id": item.id,
            "recommendation_id": item.recommendation_id,
            "actor_user_id": item.actor_user_id,
            "action": item.action,
            "reason": item.reason,
            "before_state": item.before_state,
            "after_state": item.after_state,
            "outcome_metrics": item.outcome_metrics,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }

    @classmethod
    def _owned(cls, db: Session, recommendation_id: int, user_id: int) -> OperationalRecommendation:
        recommendation = db.query(OperationalRecommendation).filter(
            OperationalRecommendation.id == recommendation_id,
            OperationalRecommendation.user_id == user_id,
        ).first()
        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        return recommendation

    @classmethod
    def _timeline(
        cls,
        db: Session,
        recommendation: OperationalRecommendation,
        actor_user_id: int,
        action: str,
        reason: str | None,
        before: dict[str, Any],
    ) -> None:
        db.add(GovernanceTimelineEntry(
            user_id=recommendation.user_id,
            recommendation_id=recommendation.id,
            actor_user_id=actor_user_id,
            action=action,
            reason=reason,
            before_state=before,
            after_state=cls.serialize_recommendation(recommendation),
        ))
