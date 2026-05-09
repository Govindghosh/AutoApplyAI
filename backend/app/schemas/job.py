from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, HttpUrl
from app.models.job import JobStatus

class JobBase(BaseModel):
    source_id: str
    title: str
    company: str
    location: Optional[str] = None
    description: Optional[str] = None
    salary: Optional[str] = None
    url: str
    source: str
    remote_type: Optional[str] = None

class JobCreate(JobBase):
    raw_data: Optional[Dict[str, Any]] = None

class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    ai_score: Optional[float] = None
    ai_analysis: Optional[Dict[str, Any]] = None

class JobResponse(JobBase):
    id: int
    status: JobStatus
    ai_score: Optional[float] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schema for AI Analysis Output (V2)
class AIAnalysisOutput(BaseModel):
    match_score: float # Overall weighted score
    
    # Sub-scores (Deterministic + AI enriched)
    skills_match: float
    experience_match: float
    location_match: float
    tech_stack_match: float
    
    missing_keywords: list[str]
    resume_improvements: list[str]
    risk_level: str # e.g., "low", "medium", "high"
    justification: str
