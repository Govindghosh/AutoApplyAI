from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, field_validator
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: JobStatus
    ai_score: Optional[float] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    analysis_attempts: int = 0
    analysis_error: Optional[str] = None
    last_analysis_model: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator("analysis_attempts", mode="before")
    @classmethod
    def default_analysis_attempts(cls, value: Any) -> int:
        return 0 if value is None else value


class JobSourceSummary(BaseModel):
    source: str
    count: int
    supported: bool = True


# Schema for AI Analysis Output (V2)
class AIAnalysisOutput(BaseModel):
    match_score: float  # Overall weighted score

    # Sub-scores (Deterministic + AI enriched)
    skills_match: float
    experience_match: float
    location_match: float
    tech_stack_match: float

    missing_keywords: list[str]
    resume_improvements: list[str]
    risk_level: str  # e.g., "low", "medium", "high"
    justification: str
