from typing import Any, Dict

from playwright.async_api import Page

from app.automation.ats.base import ATSAdapter
from app.automation.workflow_primitives import WorkflowPrimitives

class GreenhouseAdapter(ATSAdapter):
    """
    High-fidelity automation driver for the Greenhouse ATS platform.
    Refactored to use standard WorkflowPrimitives for orchestration compression.
    """
    platform = "Greenhouse"
    selector_catalog = {
        "first_name": "#first_name",
        "last_name": "#last_name",
        "email": "#email",
        "phone": "#phone",
        "resume": "input[type='file'][name='resume']",
        "submit_button": "#submit_app",
    }
    
    async def navigate(self, page: Page, url: str):
        await WorkflowPrimitives.navigate_with_retry(page, url, "Greenhouse")

    async def fill_personal_info(self, page: Page, profile: Dict[str, Any]):
        mappings = {
            "#first_name": profile.get("first_name"),
            "#last_name": profile.get("last_name"),
            "#email": profile.get("email"),
            "#phone": profile.get("phone"),
        }
        
        for selector, value in mappings.items():
            if value:
                await WorkflowPrimitives.fill_field(page, selector, value, "Greenhouse")

    async def upload_resume(self, page: Page, resume_path: str):
        await WorkflowPrimitives.upload_file(page, "input[type='file'][name='resume']", resume_path, "Greenhouse")

    async def handle_custom_questions(self, page: Page, ai_answers: Dict[str, str]):
        # Implementation continues using primitives...
        pass

    async def submit(self, page: Page) -> bool:
        try:
            await WorkflowPrimitives.click_button(page, self.selector_catalog["submit_button"], "Greenhouse")
            return True
        except:
            return False
