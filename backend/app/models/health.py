from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class SelectorHealth(Base):
    __tablename__ = "selector_health"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, index=True) # Greenhouse, Lever, etc.
    selector_name = Column(String, index=True) # e.g., "submit_button"
    
    # Reliability Metrics
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    success_rate = Column(Float, default=1.0)
    
    # Drift Indicators
    last_success = Column(DateTime(timezone=True))
    last_failure = Column(DateTime(timezone=True))
    
    # Assisted Adaptation Data
    last_known_working_dom = Column(JSON, nullable=True) # Snapshots for comparison
    suggested_replacement = Column(String, nullable=True) # Safe suggestion for human approval
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
