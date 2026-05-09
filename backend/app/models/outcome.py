from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from app.core.database import Base

class ApplicationOutcome(Base):
    __tablename__ = "application_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    user_id = Column(Integer, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    
    # Outcome Data
    status = Column(String) # INTERVIEW, REJECTION, GHOSTED, CALLBACK, OFFER
    note = Column(String, nullable=True)
    
    # Snapshot of context for correlation
    ai_score_at_apply = Column(Float)
    job_source = Column(String)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
