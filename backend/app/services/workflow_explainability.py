from __future__ import annotations

from typing import Any

from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.automation.workflow_primitives import WorkflowPrimitiveRegistry
from app.services.orchestration_compression_service import OrchestrationCompressionService


class WorkflowExplainability:
    STEP_CATALOG: dict[str, dict[str, Any]] = {
        "NAVIGATE_TO_JOB": {
            "label": "Navigate to job",
            "autonomy": "autonomous",
            "summary": "Opening the job posting and preparing a browser checkpoint.",
            "data_used": ["job URL", "source platform"],
            "checkpoint": "Job page loaded",
            "risk_level": "low",
        },
        "AUTH_CHECK": {
            "label": "Authentication check",
            "autonomy": "supervised",
            "summary": "Checking whether the application site needs a login or identity challenge.",
            "data_used": ["browser session", "source platform"],
            "checkpoint": "Access state verified",
            "risk_level": "medium",
        },
        "UPLOAD_RESUME": {
            "label": "Upload resume",
            "autonomy": "autonomous",
            "summary": "Uploading the selected resume once and recording the upload checkpoint.",
            "data_used": ["selected resume", "job URL"],
            "checkpoint": "Resume upload",
            "risk_level": "medium",
        },
        "FILL_BASIC_INFO": {
            "label": "Fill basic info",
            "autonomy": "autonomous",
            "summary": "Filling standard profile fields from approved profile data.",
            "data_used": ["approved profile", "locked profile fields"],
            "checkpoint": "Basic profile fields",
            "risk_level": "medium",
        },
        "HANDLE_CUSTOM_QUESTIONS": {
            "label": "Handle custom questions",
            "autonomy": "supervised",
            "summary": "Answering known questions and pausing when a question is ambiguous.",
            "data_used": ["job description", "approved profile", "resume text"],
            "checkpoint": "Custom questions",
            "risk_level": "high",
        },
        "SUBMIT_APPLICATION": {
            "label": "Final approval",
            "autonomy": "approval_required",
            "summary": "Holding before final submission until the user approves the checkpoint.",
            "data_used": ["completed form", "resume upload checkpoint", "profile fields"],
            "checkpoint": "Final submit gate",
            "risk_level": "high",
        },
        "VERIFY_SUBMISSION": {
            "label": "Verify submission",
            "autonomy": "autonomous",
            "summary": "Checking the post-submit state and recording the final outcome.",
            "data_used": ["confirmation page", "application status"],
            "checkpoint": "Submission confirmation",
            "risk_level": "medium",
        },
    }

    @classmethod
    def describe_workflow(
        cls,
        workflow: ApplicationWorkflow,
        steps: list[WorkflowStep],
    ) -> dict[str, Any]:
        active_step = next(
            (
                step
                for step in steps
                if step.status
                in [
                    WorkflowStatus.RUNNING,
                    WorkflowStatus.PAUSED_FOR_HUMAN,
                    WorkflowStatus.FAILED,
                ]
            ),
            None,
        )
        completed_steps = len([step for step in steps if step.status == WorkflowStatus.COMPLETED])
        total_steps = len(steps)

        status_value = cls._status_value(workflow.status)
        headline_map = {
            WorkflowStatus.PENDING.value: "Queued for orchestration",
            WorkflowStatus.RUNNING.value: "Automation is executing a checkpoint",
            WorkflowStatus.PAUSED_FOR_HUMAN.value: "Paused for user approval",
            WorkflowStatus.COMPLETED.value: "Workflow completed",
            WorkflowStatus.FAILED.value: "Workflow needs recovery",
            WorkflowStatus.SKIPPED.value: "Workflow skipped",
        }

        return {
            "headline": headline_map.get(status_value, "Workflow state updated"),
            "status_text": status_value.replace("_", " ").title(),
            "canonical_state": OrchestrationCompressionService.workflow_state(workflow.status),
            "active_step_id": active_step.id if active_step else None,
            "active_step_name": active_step.name if active_step else None,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "progress_percent": round((completed_steps / total_steps) * 100) if total_steps else 0,
            "autonomy_boundary": (
                "Final submission and ambiguous questions require user approval. "
                "Completed checkpoints are replay-safe and should not duplicate work."
            ),
        }

    @classmethod
    def describe_step(cls, step: WorkflowStep) -> dict[str, Any]:
        catalog = cls.STEP_CATALOG.get(
            step.name,
            {
                "label": step.name.replace("_", " ").title(),
                "autonomy": "supervised",
                "summary": "Executing a workflow checkpoint.",
                "data_used": ["workflow state"],
                "checkpoint": "Workflow checkpoint",
                "risk_level": "medium",
            },
        )

        status_value = cls._status_value(step.status)
        recovery_hint = cls._recovery_hint(step)
        why = cls._why(step, catalog)
        primitive = WorkflowPrimitiveRegistry.for_step(step.name)
        output_data = step.output_data or {}

        return {
            "label": catalog["label"],
            "status_text": status_value.replace("_", " ").title(),
            "canonical_state": OrchestrationCompressionService.workflow_state(step.status),
            "autonomy": catalog["autonomy"],
            "summary": catalog["summary"],
            "why": why,
            "data_used": catalog["data_used"],
            "checkpoint": catalog["checkpoint"],
            "risk_level": catalog["risk_level"],
            "recovery_hint": recovery_hint,
            "next_action": cls._next_action(step),
            "primitive": primitive.to_dict() if primitive else None,
            "escalation": output_data.get("escalation"),
            "recovery_recommendation": output_data.get("recovery_recommendation"),
        }

    @staticmethod
    def _status_value(status: Any) -> str:
        return status.value if hasattr(status, "value") else str(status)

    @classmethod
    def _why(cls, step: WorkflowStep, catalog: dict[str, Any]) -> str:
        status_value = cls._status_value(step.status)

        if status_value == WorkflowStatus.COMPLETED.value:
            return f"{catalog['checkpoint']} completed successfully."
        if status_value == WorkflowStatus.RUNNING.value:
            return catalog["summary"]
        if status_value == WorkflowStatus.PAUSED_FOR_HUMAN.value:
            if step.error_log:
                return step.error_log
            return "This checkpoint can change what gets submitted, so it is waiting for explicit approval."
        if status_value == WorkflowStatus.FAILED.value:
            return step.error_log or "The checkpoint failed before a durable completion signal was recorded."

        return "This checkpoint has not started yet."

    @classmethod
    def _next_action(cls, step: WorkflowStep) -> dict[str, str | None]:
        status_value = cls._status_value(step.status)

        if status_value == WorkflowStatus.FAILED.value:
            return {
                "type": "retry",
                "label": "Replay checkpoint",
            }
        if status_value == WorkflowStatus.PAUSED_FOR_HUMAN.value:
            return {
                "type": "approve",
                "label": "Review and approve",
            }
        if status_value == WorkflowStatus.RUNNING.value:
            return {
                "type": "wait",
                "label": "Running",
            }

        return {
            "type": "none",
            "label": None,
        }

    @classmethod
    def _recovery_hint(cls, step: WorkflowStep) -> str | None:
        status_value = cls._status_value(step.status)

        if status_value == WorkflowStatus.COMPLETED.value:
            return "This checkpoint is complete; replay will resume from the next incomplete step."
        if status_value == WorkflowStatus.PAUSED_FOR_HUMAN.value:
            return "Approve the checkpoint when the visible form state matches what you expect."
        if status_value != WorkflowStatus.FAILED.value:
            return None

        error = (step.error_log or "").lower()
        if "captcha" in error:
            return "Captcha interrupted the application. Completed checkpoints remain recorded; resume from this step after solving it."
        if "upload" in error or "file" in error:
            return "Resume upload did not finish. Replay this checkpoint after confirming the resume file is available."
        if "auth" in error or "login" in error:
            return "The site needs authentication. Sign in, then replay this checkpoint."
        if "timeout" in error:
            return "The site did not respond in time. Replay this checkpoint; completed prior steps will be preserved."
        if "selector" in error or "element" in error:
            return "The site layout changed. Report this node so the selector can be inspected, then retry if the page looks stable."

        return "Replay from this checkpoint. Earlier completed checkpoints are preserved by the workflow state."
