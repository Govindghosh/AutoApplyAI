from abc import ABC, abstractmethod
from playwright.async_api import Page
from typing import Dict, Any, Optional
from app.core.logging import logger

class ATSAdapter(ABC):
    """
    Abstract Base Class for ATS-specific automation drivers.
    Enforces a capability-based interface for distributed orchestration.
    """
    platform = "Generic"
    selector_catalog: Dict[str, str] = {}
    
    @abstractmethod
    async def navigate(self, page: Page, url: str):
        pass

    @abstractmethod
    async def fill_personal_info(self, page: Page, profile: Dict[str, Any]):
        pass

    @abstractmethod
    async def upload_resume(self, page: Page, resume_path: str):
        pass

    @abstractmethod
    async def handle_custom_questions(self, page: Page, ai_answers: Dict[str, str]):
        """
        Handles platform-specific custom questions (e.g., multi-select, free-text).
        Should return a list of unhandled questions for human escalation.
        """
        pass

    @abstractmethod
    async def submit(self, page: Page) -> bool:
        pass

    def log_selector_failure(self, selector_name: str, platform: str):
        """
        Telemetry hook for tracking DOM drift and selector health.
        """
        from app.services.health_service import HealthService
        logger.warning(f"Selector failure: {selector_name} on {platform}")
        HealthService.record_failure(platform, selector_name)

    def log_selector_success(self, selector_name: str, platform: str):
        """
        Records successful interaction for health scoring.
        """
        from app.services.health_service import HealthService
        HealthService.record_success(platform, selector_name)

    def capability_profile(self) -> Dict[str, Any]:
        """
        Declares governance and telemetry compatibility for certification.
        This metadata is advisory; workflow determinism remains in the orchestrator.
        """
        return {
            "platform": self.platform,
            "primitive_compliance": {
                "uses_workflow_primitives": True,
                "required_primitives": [
                    "browser.navigate_with_retry",
                    "form.fill_field",
                    "form.upload_file",
                    "form.click_button",
                    "escalation.human_input_required",
                ],
            },
            "telemetry_instrumentation": {
                "selector_health_hooks": True,
                "events": ["selector_success", "selector_failure"],
            },
            "health_scoring": {
                "capability_scored": True,
                "selector_catalog": self.selector_catalog,
            },
            "recovery_semantics": {
                "checkpoint_replay_safe": True,
                "recovery_templates": ["replay_checkpoint", "manual_escalation", "terminate_safely"],
            },
            "governance_compatibility": {
                "mandatory_final_approval": True,
                "direct_submission_allowed": False,
                "mutation_allowed": False,
            },
        }
