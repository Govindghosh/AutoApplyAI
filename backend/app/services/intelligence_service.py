from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.outcome import ApplicationOutcome
from app.models.job import Job
from typing import Dict, Any, List

class IntelligenceService:
    @staticmethod
    def get_source_performance(db: Session, user_id: int) -> List[Dict[str, Any]]:
        """
        Calculates conversion rates per job source (Wellfound, RemoteOK, etc.)
        """
        results = db.query(
            ApplicationOutcome.job_source,
            func.count(ApplicationOutcome.id).label("total"),
            func.count(ApplicationOutcome.id).filter(ApplicationOutcome.status == "INTERVIEW").label("interviews")
        ).filter(ApplicationOutcome.user_id == user_id).group_by(ApplicationOutcome.job_source).all()
        
        return [
            {
                "source": r.job_source,
                "total_apps": r.total,
                "interviews": r.interviews,
                "conversion_rate": round((r.interviews / r.total * 100), 2) if r.total > 0 else 0
            } for r in results
        ]

    @staticmethod
    def get_score_correlation(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Analyzes if higher AI match scores actually lead to more interviews.
        """
        # Bucket by score ranges
        ranges = [(0, 50), (50, 75), (75, 90), (90, 101)]
        correlation_data = []
        
        for low, high in ranges:
            stats = db.query(
                func.count(ApplicationOutcome.id).label("total"),
                func.count(ApplicationOutcome.id).filter(ApplicationOutcome.status == "INTERVIEW").label("interviews")
            ).filter(
                ApplicationOutcome.user_id == user_id,
                ApplicationOutcome.ai_score_at_apply >= low,
                ApplicationOutcome.ai_score_at_apply < high
            ).first()
            
            correlation_data.append({
                "range": f"{low}-{high-1}",
                "total": stats.total or 0,
                "interviews": stats.interviews or 0,
                "rate": round((stats.interviews / stats.total * 100), 2) if stats.total and stats.total > 0 else 0
            })
            
        return correlation_data

    @staticmethod
    def get_resume_performance(db: Session, user_id: int) -> List[Dict[str, Any]]:
        """
        Ranks resume variants by their real-world callback success.
        """
        results = db.query(
            ApplicationOutcome.resume_id,
            func.count(ApplicationOutcome.id).label("total"),
            func.count(ApplicationOutcome.id).filter(ApplicationOutcome.status == "INTERVIEW").label("interviews")
        ).filter(ApplicationOutcome.user_id == user_id).group_by(ApplicationOutcome.resume_id).all()
        
        return [
            {
                "resume_id": r.resume_id,
                "total_apps": r.total,
                "interviews": r.interviews,
                "success_rate": round((r.interviews / r.total * 100), 2) if r.total > 0 else 0
            } for r in results
        ]

    @staticmethod
    def get_actionable_insights(db: Session, user_id: int) -> List[Dict[str, Any]]:
        """
        Generates high-leverage operational recommendations based on outcome data.
        Focuses on statistical significance and decision support.
        """
        insights = []
        
        # 1. Source vs Resume Intelligence
        source_resume_stats = db.query(
            ApplicationOutcome.job_source,
            ApplicationOutcome.resume_id,
            func.count(ApplicationOutcome.id).label("total"),
            func.count(ApplicationOutcome.id).filter(ApplicationOutcome.status == "INTERVIEW").label("interviews")
        ).filter(ApplicationOutcome.user_id == user_id).group_by(
            ApplicationOutcome.job_source, ApplicationOutcome.resume_id
        ).all()
        
        for r in source_resume_stats:
            if r.total >= 5: # Minimum sample size for an insight
                rate = (r.interviews / r.total)
                if rate > 0.15: # High performance threshold
                    insights.append({
                        "type": "STRATEGY_BOOST",
                        "severity": "success",
                        "message": f"Resume variant {r.resume_id} is seeing high callback rates ({round(rate*100)}%) on {r.job_source}.",
                        "action": f"Prioritize {r.job_source} applications using this variant."
                    })
        
        # 2. Match Engine Health
        high_score_apps = db.query(
            func.count(ApplicationOutcome.id).label("total"),
            func.count(ApplicationOutcome.id).filter(ApplicationOutcome.status == "INTERVIEW").label("interviews")
        ).filter(
            ApplicationOutcome.user_id == user_id,
            ApplicationOutcome.ai_score_at_apply >= 85
        ).first()
        
        if high_score_apps.total and high_score_apps.total > 10:
            rate = high_score_apps.interviews / high_score_apps.total
            if rate < 0.05: # Low correlation warning
                insights.append({
                    "type": "MATCH_ENGINE_WARNING",
                    "severity": "warning",
                    "message": "High AI scores (85+) are currently showing low callback correlation.",
                    "action": "Review and tighten your 'Locked Fields' to improve AI alignment."
                })
        
        if not insights:
            insights.append({
                "type": "GATHERING_DATA",
                "severity": "info",
                "message": "The system is currently gathering outcome data.",
                "action": "Record more application outcomes to unlock actionable insights."
            })
            
        return insights
