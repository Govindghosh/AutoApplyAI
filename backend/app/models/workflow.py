from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class WorkflowStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED_FOR_HUMAN = "PAUSED_FOR_HUMAN"
    SKIPPED = "SKIPPED"

class ApplicationWorkflow(Base):
    __tablename__ = "application_workflows"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    user_id = Column(Integer, index=True)
    
    # Overall Workflow State
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.PENDING)
    current_step_index = Column(Integer, default=0)
    
    # Metadata
    platform_type = Column(String) # Greenhouse, Lever, etc.
    session_id = Column(String, nullable=True) # Playwright session reference
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("application_workflows.id"), index=True)
    
    name = Column(String) # e.g., "UPLOAD_RESUME", "FILL_PERSONAL_INFO"
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.PENDING)
    
    # Step Data & Snapshots
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_log = Column(String, nullable=True)
    
    # Performance Telemetry
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer, nullable=True)
    
    attempts = Column(Integer, default=0)
