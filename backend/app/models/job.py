import enum
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Enum, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class JobStatus(str, enum.Enum):
    SCRAPED = "SCRAPED"
    ANALYSIS_PENDING = "ANALYSIS_PENDING"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    SHORTLISTED = "SHORTLISTED"
    READY_TO_APPLY = "READY_TO_APPLY"
    APPLYING = "APPLYING"
    APPLYING_PENDING_APPROVAL = "APPLYING_PENDING_APPROVAL"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    INTERVIEW = "INTERVIEW"
    REJECTED = "REJECTED"

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, index=True, unique=True) # ID from the job board
    title = Column(String, index=True, nullable=False)
    company = Column(String, index=True, nullable=False)
    location = Column(String)
    description = Column(Text)
    salary = Column(String)
    url = Column(String, unique=True, index=True)
    source = Column(String) # e.g., "RemoteOK", "Wellfound"
    remote_type = Column(String)
    
    status = Column(Enum(JobStatus), default=JobStatus.SCRAPED, nullable=False)
    
    # AI Enrichment
    ai_score = Column(Float, index=True)
    ai_analysis = Column(JSON) # Structured JSON from AI
    
    # AI Pipeline Telemetry
    analysis_attempts = Column(Integer, default=0)
    analysis_error = Column(Text)
    analyzed_at = Column(DateTime(timezone=True))
    last_analysis_model = Column(String)
    applied_resume_id = Column(Integer, index=True) # ID of the resume used for the application
    
    # Metadata
    raw_data = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
