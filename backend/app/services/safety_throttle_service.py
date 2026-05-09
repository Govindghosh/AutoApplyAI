from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workflow import ApplicationWorkflow, WorkflowStatus


class SafetyThrottleService:
    ACTIVE_STATUSES = [
        WorkflowStatus.PENDING,
        WorkflowStatus.RUNNING,
        WorkflowStatus.PAUSED_FOR_HUMAN,
    ]

    @classmethod
    def get_usage(cls, db: Session, user: User) -> dict[str, Any]:
        day_start = datetime.combine(
            datetime.now(timezone.utc).date(),
            time.min,
            tzinfo=timezone.utc,
        )

        daily_started = db.query(ApplicationWorkflow).filter(
            ApplicationWorkflow.user_id == user.id,
            ApplicationWorkflow.created_at >= day_start,
        ).count()

        active_workflows = db.query(ApplicationWorkflow).filter(
            ApplicationWorkflow.user_id == user.id,
            ApplicationWorkflow.status.in_(cls.ACTIVE_STATUSES),
        ).count()

        daily_limit = user.daily_application_limit or 5
        concurrency_limit = user.concurrency_limit or 2

        return {
            "daily_started": daily_started,
            "daily_limit": daily_limit,
            "daily_remaining": max(daily_limit - daily_started, 0),
            "active_workflows": active_workflows,
            "concurrency_limit": concurrency_limit,
            "concurrency_remaining": max(concurrency_limit - active_workflows, 0),
        }

    @classmethod
    def evaluate(cls, db: Session, user: User) -> dict[str, Any]:
        usage = cls.get_usage(db, user)
        blocked_reasons: list[str] = []

        if usage["daily_remaining"] <= 0:
            blocked_reasons.append("daily_limit_reached")

        if usage["concurrency_remaining"] <= 0:
            blocked_reasons.append("concurrency_limit_reached")

        return {
            **usage,
            "allowed": not blocked_reasons,
            "blocked_reasons": blocked_reasons,
        }
