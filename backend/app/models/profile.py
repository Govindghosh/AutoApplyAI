from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Structured Canonical Data
    full_name = Column(String)
    title = Column(String)
    experience_years = Column(Integer)
    skills = Column(JSON) # List of strings: ["Python", "FastAPI"]
    tech_stack = Column(JSON) # Detailed tech stack: {"backend": ["FastAPI"], "db": ["PostgreSQL"]}
    
    # Preferences
    preferred_roles = Column(JSON)
    preferred_locations = Column(JSON)
    remote_preference = Column(String, default="Remote")
    salary_expectation = Column(Integer)
    preferred_currency = Column(String, default="USD")
    work_authorization = Column(String)
    
    # Metadata
    bio = Column(Text)
    locked_fields = Column(JSON, default=list) # List of fields AI cannot overwrite: ["full_name", "salary_expectation"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="profile")
    resumes = relationship("Resume", back_populates="profile")

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("resumes.id"), nullable=True) # Lineage tracking
    
    name = Column(String, nullable=False) # e.g., "Main Resume", "Backend Variant"
    content_text = Column(Text, nullable=False) # Extracted text for AI analysis
    file_path = Column(String) # Path to PDF/Docx
    
    # Versioning & Type
    version = Column(Integer, default=1)
    is_base = Column(Boolean, default=False)
    
    # Optimization metadata
    is_optimized = Column(Boolean, default=False)
    optimization_prompt = Column(Text) # Prompt used for optimization
    optimization_notes = Column(Text)
    
    # Metadata
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True) # For job-specific variants
    # Extraction & Review
    extraction_status = Column(String, default="PENDING") # PENDING, PROCESSING, COMPLETED, REVIEW_REQUIRED, FAILED
    extraction_data = Column(JSON) # The raw AI extraction candidate
    confidence_scores = Column(JSON) # Field-level confidence: {"skills": 0.95, "experience_years": 0.8}
    review_status = Column(String, default="NOT_STARTED") # NOT_STARTED, IN_PROGRESS, REVIEWED
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    profile = relationship("UserProfile", back_populates="resumes")
    parent = relationship("Resume", remote_side=[id], backref="variants")
    job = relationship("Job")
