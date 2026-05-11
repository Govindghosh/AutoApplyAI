from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class EventCategory(str, Enum):
    WORKFLOW = "workflow"
    OPERATIONAL = "operational"
    GOVERNANCE = "governance"
    BEHAVIORAL = "behavioral"
    RELIABILITY = "reliability"


@dataclass(frozen=True)
class EventSchema:
    category: EventCategory
    required_fields: tuple[str, ...]
    retention_days: int
    compression_strategy: str
    archival_strategy: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data


class EventTaxonomyService:
    """
    Consolidated event taxonomy for workflow, operational, governance,
    behavioral, and reliability signals.

    The validator is intentionally non-blocking: it identifies schema drift
    without dropping events, preserving telemetry determinism during rollout.
    """

    DEFAULT_SCHEMA = EventSchema(
        category=EventCategory.OPERATIONAL,
        required_fields=(),
        retention_days=30,
        compression_strategy="count_by_type_and_resource",
        archival_strategy="cold_store_after_retention",
        description="Unclassified operational event.",
    )

    EVENT_SCHEMAS: dict[str, EventSchema] = {
        "JOB_SCRAPED": EventSchema(
            EventCategory.WORKFLOW,
            ("job_id",),
            90,
            "state_transition_rollup",
            "archive_payload_after_90_days",
            "Job ingestion state transition.",
        ),
        "JOB_ANALYZING": EventSchema(
            EventCategory.WORKFLOW,
            ("job_id",),
            90,
            "state_transition_rollup",
            "archive_payload_after_90_days",
            "Job analysis state transition.",
        ),
        "JOB_ANALYZED": EventSchema(
            EventCategory.WORKFLOW,
            ("job_id",),
            90,
            "state_transition_rollup",
            "archive_payload_after_90_days",
            "Completed job analysis state transition.",
        ),
        "JOB_FAILED": EventSchema(
            EventCategory.RELIABILITY,
            (),
            180,
            "failure_signature_rollup",
            "retain_payload_for_incident_review",
            "Job-level failure signal.",
        ),
        "APPLYING_STARTED": EventSchema(
            EventCategory.WORKFLOW,
            ("workflow_id",),
            90,
            "state_transition_rollup",
            "archive_payload_after_90_days",
            "Workflow execution started.",
        ),
        "APPLYING_PENDING_APPROVAL": EventSchema(
            EventCategory.GOVERNANCE,
            ("workflow_id",),
            180,
            "approval_boundary_rollup",
            "retain_payload_for_audit",
            "Application submission is gated by approval.",
        ),
        "APPLYING_SUCCESS": EventSchema(
            EventCategory.WORKFLOW,
            (),
            90,
            "state_transition_rollup",
            "archive_payload_after_90_days",
            "Application workflow completed successfully.",
        ),
        "APPLYING_FAILED": EventSchema(
            EventCategory.RELIABILITY,
            (),
            180,
            "failure_signature_rollup",
            "retain_payload_for_incident_review",
            "Application workflow failed.",
        ),
        "WORKFLOW_TRACE_EXPORTED": EventSchema(
            EventCategory.GOVERNANCE,
            ("workflow_id",),
            365,
            "audit_count_rollup",
            "retain_payload_for_audit",
            "User exported an explainability trace.",
        ),
        "WORKFLOW_NODE_REPORTED": EventSchema(
            EventCategory.BEHAVIORAL,
            ("workflow_id", "step_id", "step_name"),
            180,
            "node_feedback_rollup",
            "archive_payload_after_180_days",
            "User reported confusing or incorrect node behavior.",
        ),
        "WORKFLOW_CHECKPOINT_REPLAYED": EventSchema(
            EventCategory.RELIABILITY,
            ("workflow_id", "step_id", "step_name"),
            180,
            "replay_chain_rollup",
            "retain_payload_for_incident_review",
            "Workflow checkpoint replay was requested.",
        ),
        "WORKFLOW_TERMINATED": EventSchema(
            EventCategory.RELIABILITY,
            ("workflow_id",),
            180,
            "termination_reason_rollup",
            "retain_payload_for_incident_review",
            "Workflow was safely terminated.",
        ),
        "WORKFLOW_ESCALATION_CREATED": EventSchema(
            EventCategory.GOVERNANCE,
            ("workflow_id", "step_id", "template"),
            180,
            "escalation_template_rollup",
            "retain_payload_for_audit",
            "Workflow paused behind a standard escalation template.",
        ),
        "WORKFLOW_RECOVERY_RECOMMENDED": EventSchema(
            EventCategory.RELIABILITY,
            ("workflow_id", "action", "confidence"),
            180,
            "recovery_action_rollup",
            "retain_payload_for_incident_review",
            "Shortest safe recovery path was recommended.",
        ),
        "WORKFLOW_PRIMITIVE_EXECUTED": EventSchema(
            EventCategory.OPERATIONAL,
            ("primitive", "version"),
            90,
            "primitive_usage_rollup",
            "archive_payload_after_90_days",
            "Registered orchestration primitive was executed.",
        ),
        "AUTOMATION_THROTTLED": EventSchema(
            EventCategory.OPERATIONAL,
            (),
            90,
            "capacity_window_rollup",
            "archive_payload_after_90_days",
            "Automation was throttled by safety or capacity policy.",
        ),
        "ONBOARDING_COMPLETED": EventSchema(
            EventCategory.BEHAVIORAL,
            (),
            180,
            "user_action_rollup",
            "archive_payload_after_180_days",
            "User completed onboarding.",
        ),
        "PRODUCT_TELEMETRY": EventSchema(
            EventCategory.BEHAVIORAL,
            ("event_type",),
            90,
            "user_action_rollup",
            "archive_payload_after_90_days",
            "Generic product telemetry event.",
        ),
        "PROFILE_SYNCED": EventSchema(
            EventCategory.WORKFLOW,
            (),
            90,
            "state_transition_rollup",
            "archive_payload_after_90_days",
            "Profile synchronization completed.",
        ),
        "RESUME_PROCESSING": EventSchema(
            EventCategory.WORKFLOW,
            ("resume_id",),
            90,
            "state_transition_rollup",
            "archive_payload_after_90_days",
            "Resume processing started.",
        ),
        "RESUME_REVIEW_REQUIRED": EventSchema(
            EventCategory.GOVERNANCE,
            ("resume_id",),
            180,
            "approval_boundary_rollup",
            "retain_payload_for_audit",
            "Resume extraction requires human review.",
        ),
        "RESUME_COMPLETED": EventSchema(
            EventCategory.WORKFLOW,
            ("resume_id",),
            90,
            "state_transition_rollup",
            "archive_payload_after_90_days",
            "Resume review or processing completed.",
        ),
        "SYSTEM_ALERT": EventSchema(
            EventCategory.OPERATIONAL,
            ("message", "severity"),
            90,
            "alert_signature_rollup",
            "retain_payload_for_incident_review",
            "System health or operator alert.",
        ),
    }

    @classmethod
    def schema_for(cls, event_type: str) -> EventSchema:
        return cls.EVENT_SCHEMAS.get(event_type, cls.DEFAULT_SCHEMA)

    @classmethod
    def category_for(cls, event_type: str) -> str:
        return cls.schema_for(event_type).category.value

    @classmethod
    def validate_payload(cls, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        schema = cls.schema_for(event_type)
        missing = [
            field
            for field in schema.required_fields
            if payload.get(field) is None
        ]
        return {
            "valid": not missing,
            "missing_fields": missing,
            "category": schema.category.value,
            "schema_version": "1.0.0",
            "retention_days": schema.retention_days,
            "compression_strategy": schema.compression_strategy,
            "archival_strategy": schema.archival_strategy,
        }

    @classmethod
    def catalog(cls) -> dict[str, Any]:
        categories = {
            category.value: {
                "purpose": cls._purpose(category),
                "events": [],
            }
            for category in EventCategory
        }
        for event_type, schema in cls.EVENT_SCHEMAS.items():
            categories[schema.category.value]["events"].append(
                {
                    "event_type": event_type,
                    **schema.to_dict(),
                }
            )
        return categories

    @classmethod
    def summarize_events(cls, events: list[Any]) -> dict[str, Any]:
        category_counts = Counter(cls.category_for(event.event_type) for event in events)
        event_counts = Counter(event.event_type for event in events)
        validation_warnings = []

        for event in events:
            validation = cls.validate_payload(event.event_type, event.payload or {})
            if not validation["valid"]:
                validation_warnings.append(
                    {
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "missing_fields": validation["missing_fields"],
                    }
                )

        return {
            "categories": [
                {"category": category, "count": count}
                for category, count in category_counts.most_common()
            ],
            "top_events": [
                {"event_type": event_type, "count": count}
                for event_type, count in event_counts.most_common(10)
            ],
            "validation_warnings": validation_warnings[:20],
            "retention_policies": cls.retention_policies(),
            "compression": {
                "strategy": "roll up by category, event type, resource, and day",
                "lossless_window_days": 30,
                "archive_after_days": min(schema.retention_days for schema in cls.EVENT_SCHEMAS.values()),
            },
        }

    @classmethod
    def retention_policies(cls) -> list[dict[str, Any]]:
        by_category: dict[str, set[int]] = {}
        for schema in cls.EVENT_SCHEMAS.values():
            by_category.setdefault(schema.category.value, set()).add(schema.retention_days)

        return [
            {
                "category": category,
                "retention_days": max(days),
                "policy": "retain payload through retention window, then archive rollups",
            }
            for category, days in sorted(by_category.items())
        ]

    @staticmethod
    def _purpose(category: EventCategory) -> str:
        return {
            EventCategory.WORKFLOW: "State transitions and workflow lifecycle.",
            EventCategory.OPERATIONAL: "Infrastructure and runtime health.",
            EventCategory.GOVERNANCE: "Approvals, reviews, and audit boundaries.",
            EventCategory.BEHAVIORAL: "User interaction and trust patterns.",
            EventCategory.RELIABILITY: "Drift, failure, replay, and recovery telemetry.",
        }[category]
