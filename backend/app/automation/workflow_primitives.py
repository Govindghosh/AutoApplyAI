from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Coroutine

from playwright.async_api import Page

from app.core.logging import logger
from app.services.health_service import HealthService


class PrimitiveKind(str, Enum):
    NAVIGATION = "navigation"
    RETRY = "retry"
    UPLOAD = "upload"
    FORM_FILL = "form_fill"
    ESCALATION = "escalation"
    RECOVERY = "recovery"
    VALIDATION = "validation"
    CHECKPOINT = "checkpoint"


class ExecutionGuarantee(str, Enum):
    BEST_EFFORT = "best_effort"
    IDEMPOTENT = "idempotent"
    EXACTLY_ONCE_GATE = "exactly_once_gate"
    HUMAN_GATED = "human_gated"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class RetrySemantics:
    max_attempts: int
    backoff_seconds: float
    retry_on: tuple[str, ...]
    raises_on_exhaustion: bool = True


@dataclass(frozen=True)
class PrimitiveMetadata:
    name: str
    version: str
    kind: PrimitiveKind
    capabilities: tuple[str, ...]
    execution_guarantee: ExecutionGuarantee
    retry: RetrySemantics
    observability_hooks: tuple[str, ...]
    description: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        data["execution_guarantee"] = self.execution_guarantee.value
        return data


class WorkflowPrimitiveRegistry:
    """
    Central registry for deterministic orchestration actions.

    ATS adapters should depend on these named primitives rather than inventing
    platform-specific action semantics. The registry is intentionally metadata
    heavy so operations, recovery, and explainability can reason about the same
    primitives workers execute.
    """

    _PRIMITIVES: dict[str, PrimitiveMetadata] = {
        "navigate.with_retry": PrimitiveMetadata(
            name="navigate.with_retry",
            version="1.0.0",
            kind=PrimitiveKind.NAVIGATION,
            capabilities=("browser_navigation", "network_idle_wait", "transient_retry"),
            execution_guarantee=ExecutionGuarantee.IDEMPOTENT,
            retry=RetrySemantics(
                max_attempts=2,
                backoff_seconds=1.5,
                retry_on=("timeout", "network", "navigation"),
            ),
            observability_hooks=("selector_health", "primitive_execution"),
            description="Open a job URL with bounded retry and navigation health telemetry.",
        ),
        "form.fill_field": PrimitiveMetadata(
            name="form.fill_field",
            version="1.0.0",
            kind=PrimitiveKind.FORM_FILL,
            capabilities=("selector_wait", "field_write", "soft_failure"),
            execution_guarantee=ExecutionGuarantee.BEST_EFFORT,
            retry=RetrySemantics(
                max_attempts=1,
                backoff_seconds=0,
                retry_on=("selector_missing",),
                raises_on_exhaustion=False,
            ),
            observability_hooks=("selector_health", "primitive_execution"),
            description="Fill one approved profile field and continue on optional field failure.",
        ),
        "upload.resume_file": PrimitiveMetadata(
            name="upload.resume_file",
            version="1.0.0",
            kind=PrimitiveKind.UPLOAD,
            capabilities=("file_upload", "checkpoint_required"),
            execution_guarantee=ExecutionGuarantee.IDEMPOTENT,
            retry=RetrySemantics(
                max_attempts=2,
                backoff_seconds=1,
                retry_on=("selector_missing", "file_upload"),
            ),
            observability_hooks=("selector_health", "checkpoint_persistence"),
            description="Upload the approved resume file and preserve upload checkpoint state.",
        ),
        "button.click": PrimitiveMetadata(
            name="button.click",
            version="1.0.0",
            kind=PrimitiveKind.VALIDATION,
            capabilities=("selector_click", "submission_boundary"),
            execution_guarantee=ExecutionGuarantee.EXACTLY_ONCE_GATE,
            retry=RetrySemantics(
                max_attempts=1,
                backoff_seconds=0,
                retry_on=("selector_missing",),
            ),
            observability_hooks=("selector_health", "primitive_execution"),
            description="Click a deterministic button when the caller has already satisfied gates.",
        ),
        "escalation.human_input_required": PrimitiveMetadata(
            name="escalation.human_input_required",
            version="1.0.0",
            kind=PrimitiveKind.ESCALATION,
            capabilities=("human_pause", "template_payload", "approval_boundary"),
            execution_guarantee=ExecutionGuarantee.HUMAN_GATED,
            retry=RetrySemantics(
                max_attempts=0,
                backoff_seconds=0,
                retry_on=(),
                raises_on_exhaustion=False,
            ),
            observability_hooks=("escalation_created", "governance_boundary"),
            description="Pause execution behind a standard human intervention template.",
        ),
        "recovery.shortest_safe_path": PrimitiveMetadata(
            name="recovery.shortest_safe_path",
            version="1.0.0",
            kind=PrimitiveKind.RECOVERY,
            capabilities=("checkpoint_replay", "manual_escalation", "safe_termination"),
            execution_guarantee=ExecutionGuarantee.IDEMPOTENT,
            retry=RetrySemantics(
                max_attempts=1,
                backoff_seconds=0,
                retry_on=("recoverable_failure",),
            ),
            observability_hooks=("recovery_recommendation", "replay_safety_validation"),
            description="Map failures to replay node, replay checkpoint, manual escalation, or safe termination.",
        ),
        "checkpoint.persist": PrimitiveMetadata(
            name="checkpoint.persist",
            version="1.0.0",
            kind=PrimitiveKind.CHECKPOINT,
            capabilities=("durable_step_state", "idempotency_guard"),
            execution_guarantee=ExecutionGuarantee.IDEMPOTENT,
            retry=RetrySemantics(
                max_attempts=1,
                backoff_seconds=0,
                retry_on=("database_transient",),
            ),
            observability_hooks=("workflow_state_transition", "checkpoint_persistence"),
            description="Persist a durable workflow checkpoint exactly once from the orchestrator.",
        ),
    }

    WORKFLOW_STEP_TO_PRIMITIVE: dict[str, str] = {
        "NAVIGATE_TO_JOB": "navigate.with_retry",
        "AUTH_CHECK": "checkpoint.persist",
        "UPLOAD_RESUME": "upload.resume_file",
        "FILL_BASIC_INFO": "form.fill_field",
        "HANDLE_CUSTOM_QUESTIONS": "escalation.human_input_required",
        "SUBMIT_APPLICATION": "escalation.human_input_required",
        "VERIFY_SUBMISSION": "checkpoint.persist",
    }

    @classmethod
    def get(cls, name: str) -> PrimitiveMetadata:
        return cls._PRIMITIVES[name]

    @classmethod
    def list(cls) -> list[dict[str, Any]]:
        return [primitive.to_dict() for primitive in cls._PRIMITIVES.values()]

    @classmethod
    def for_step(cls, step_name: str) -> PrimitiveMetadata | None:
        primitive_name = cls.WORKFLOW_STEP_TO_PRIMITIVE.get(step_name)
        if not primitive_name:
            return None
        return cls._PRIMITIVES.get(primitive_name)

    @classmethod
    def by_capability(cls, capability: str) -> list[dict[str, Any]]:
        return [
            primitive.to_dict()
            for primitive in cls._PRIMITIVES.values()
            if capability in primitive.capabilities
        ]

    @classmethod
    def reuse_ratio(cls, step_names: list[str]) -> float:
        if not step_names:
            return 100

        mapped = len([name for name in step_names if name in cls.WORKFLOW_STEP_TO_PRIMITIVE])
        return round((mapped / len(step_names)) * 100, 2)


class WorkflowPrimitives:
    """
    Library of reusable orchestration primitives to reduce duplication
    and ensure consistent execution across all ATS adapters.
    """

    registry = WorkflowPrimitiveRegistry

    @staticmethod
    async def _execute_with_retry(
        primitive_name: str,
        platform: str,
        health_key: str,
        operation: Callable[[], Coroutine[Any, Any, None]],
    ):
        primitive = WorkflowPrimitiveRegistry.get(primitive_name)
        attempts = max(primitive.retry.max_attempts, 1)
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                logger.info(
                    "Primitive %s@%s attempt %s/%s on %s",
                    primitive.name,
                    primitive.version,
                    attempt,
                    attempts,
                    platform,
                )
                await operation()
                HealthService.record_success(platform, health_key)
                return
            except Exception as exc:
                last_error = exc
                HealthService.record_failure(platform, health_key)
                if attempt < attempts and primitive.retry.backoff_seconds:
                    from asyncio import sleep

                    await sleep(primitive.retry.backoff_seconds)

        if primitive.retry.raises_on_exhaustion and last_error:
            raise last_error

        logger.warning(
            "Primitive %s exhausted without raising on %s: %s",
            primitive.name,
            platform,
            last_error,
        )
    
    @staticmethod
    async def navigate_with_retry(page: Page, url: str, platform: str):
        async def operation():
            await page.goto(url, wait_until="networkidle", timeout=60000)

        await WorkflowPrimitives._execute_with_retry(
            "navigate.with_retry",
            platform,
            "navigation",
            operation,
        )

    @staticmethod
    async def fill_field(page: Page, selector: str, value: str, platform: str):
        async def operation():
            await page.wait_for_selector(selector, timeout=5000)
            await page.fill(selector, value)

        await WorkflowPrimitives._execute_with_retry(
            "form.fill_field",
            platform,
            selector,
            operation,
        )

    @staticmethod
    async def upload_file(page: Page, selector: str, file_path: str, platform: str):
        async def operation():
            await page.set_input_files(selector, file_path)

        await WorkflowPrimitives._execute_with_retry(
            "upload.resume_file",
            platform,
            "file_upload",
            operation,
        )

    @staticmethod
    async def click_button(page: Page, selector: str, platform: str):
        async def operation():
            await page.click(selector)

        await WorkflowPrimitives._execute_with_retry(
            "button.click",
            platform,
            "button_click",
            operation,
        )
