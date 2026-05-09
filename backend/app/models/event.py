from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class SystemEvent(Base):
    __tablename__ = "system_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True) # UUID for idempotency
    user_id = Column(Integer, index=True)
    event_type = Column(String, index=True)
    resource_id = Column(String, nullable=True)
    payload = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Metadata for replay/filtering
    is_processed = Column(Boolean, default=False)
    source_worker = Column(String, nullable=True) # Which Celery worker emitted this
