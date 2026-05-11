from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.job import Job
from app.models.outcome import ApplicationOutcome
from app.services.intelligence_service import IntelligenceService
from app.services.recommendation_intelligence_service import RecommendationIntelligenceService
from pydantic import BaseModel

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

class OutcomeCreate(BaseModel):
    status: str # INTERVIEW, REJECTION, GHOSTED, CALLBACK, OFFER
    note: Optional[str] = None

@router.post("/applications/{job_id}/outcome")
async def record_outcome(
    job_id: int,
    outcome_in: OutcomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Create or update outcome
    outcome = db.query(ApplicationOutcome).filter(
        ApplicationOutcome.job_id == job_id,
        ApplicationOutcome.user_id == current_user.id
    ).first()
    
    if not outcome:
        outcome = ApplicationOutcome(
            job_id=job_id,
            user_id=current_user.id,
            resume_id=job.applied_resume_id if hasattr(job, 'applied_resume_id') else None,
            ai_score_at_apply=job.ai_score or 0.0,
            job_source=job.source,
            status=outcome_in.status,
            note=outcome_in.note
        )
        db.add(outcome)
    else:
        outcome.status = outcome_in.status
        outcome.note = outcome_in.note
        
    db.commit()
    return {"status": "success"}

@router.get("/stats")
async def get_intelligence_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return {
        "source_performance": IntelligenceService.get_source_performance(db, current_user.id),
        "score_correlation": IntelligenceService.get_score_correlation(db, current_user.id),
        "resume_performance": IntelligenceService.get_resume_performance(db, current_user.id),
        "actionable_insights": IntelligenceService.get_actionable_insights(db, current_user.id),
        "governed_recommendations": RecommendationIntelligenceService.build(db, current_user.id),
    }
