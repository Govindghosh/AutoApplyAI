from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import json
from app.core.database import SessionLocal
from app.core.logging import logger
from app.core.config import settings
from app.services.event_taxonomy_service import EventTaxonomyService
import redis

from app.utils.n8n import N8NClient

# Redis connection for event bus using central config
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
n8n_client = N8NClient()


class EventType(str, Enum):
    # Job Events
    JOB_SCRAPED = "JOB_SCRAPED"
    JOB_ANALYZING = "JOB_ANALYZING"
    JOB_ANALYZED = "JOB_ANALYZED"
    JOB_FAILED = "JOB_FAILED"

    # Resume Events
    RESUME_PROCESSING = "RESUME_PROCESSING"
    RESUME_REVIEW_REQUIRED = "RESUME_REVIEW_REQUIRED"
    RESUME_COMPLETED = "RESUME_COMPLETED"

    # Application Events
    APPLYING_STARTED = "APPLYING_STARTED"
    APPLYING_PENDING_APPROVAL = "APPLYING_PENDING_APPROVAL"
    APPLYING_SUCCESS = "APPLYING_SUCCESS"
    APPLYING_FAILED = "APPLYING_FAILED"
    WORKFLOW_TRACE_EXPORTED = "WORKFLOW_TRACE_EXPORTED"
    WORKFLOW_NODE_REPORTED = "WORKFLOW_NODE_REPORTED"
    WORKFLOW_CHECKPOINT_REPLAYED = "WORKFLOW_CHECKPOINT_REPLAYED"
    WORKFLOW_TERMINATED = "WORKFLOW_TERMINATED"
    WORKFLOW_ESCALATION_CREATED = "WORKFLOW_ESCALATION_CREATED"
    WORKFLOW_RECOVERY_RECOMMENDED = "WORKFLOW_RECOVERY_RECOMMENDED"
    WORKFLOW_PRIMITIVE_EXECUTED = "WORKFLOW_PRIMITIVE_EXECUTED"
    AUTOMATION_THROTTLED = "AUTOMATION_THROTTLED"
    ONBOARDING_COMPLETED = "ONBOARDING_COMPLETED"
    PRODUCT_TELEMETRY = "PRODUCT_TELEMETRY"

    # System Events
    PROFILE_SYNCED = "PROFILE_SYNCED"
    SYSTEM_ALERT = "SYSTEM_ALERT"


import uuid
from app.models.event import SystemEvent


class EventService:
    @staticmethod
    def emit(
        user_id: int,
        event_type: EventType,
        payload: Dict[str, Any],
        resource_id: Optional[str] = None,
        source_worker: Optional[str] = None,
    ):
        """
        Emits an operational event, persists it, and broadcasts via Redis.
        """
        evt_id = str(uuid.uuid4())
        validation = EventTaxonomyService.validate_payload(event_type.value, payload)
        if not validation["valid"]:
            logger.warning(
                "Event schema warning for %s: missing %s",
                event_type.value,
                validation["missing_fields"],
            )

        event_data = {
            "event_id": evt_id,
            "user_id": user_id,
            "type": event_type.value,
            "category": validation["category"],
            "schema_version": validation["schema_version"],
            "payload": payload,
            "resource_id": resource_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Persist to Database (Operational Truth)
        db = SessionLocal()
        try:
            db_event = SystemEvent(
                event_id=evt_id,
                user_id=user_id,
                event_type=event_type.value,
                resource_id=resource_id,
                payload=payload,
                source_worker=source_worker,
            )
            db.add(db_event)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to persist event to DB: {e}")
        finally:
            db.close()

        # 2. Broadcast via Redis (Realtime Pulse)
        try:
            channel = f"user_events:{user_id}"
            redis_client.publish(channel, json.dumps(event_data))
            logger.debug(f"Event broadcasted: {event_type} ({evt_id})")
        except Exception as e:
            logger.error(f"Failed to broadcast event: {e}")

        # 3. Forward to n8n for external workflow automation.
        n8n_client.trigger_event_background(event_type.value, event_data)

    @staticmethod
    def broadcast_system_alert(message: str, severity: str = "info"):
        """
        Broadcasts an alert to all active users.
        """
        event_data = {
            "type": EventType.SYSTEM_ALERT.value,
            "payload": {"message": message, "severity": severity},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        redis_client.publish("system_events", json.dumps(event_data))
