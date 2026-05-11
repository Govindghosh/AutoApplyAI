from app.automation.ats.base import ATSAdapter
from app.automation.workflow_primitives import WorkflowPrimitives
from playwright.async_api import Page
from typing import Dict, Any

class LeverAdapter(ATSAdapter):
    """
    High-fidelity automation driver for the Lever ATS platform.
    """
    platform = "Lever"
    selector_catalog = {
        "name": "input[name='name']",
        "email": "input[name='email']",
        "phone": "input[name='phone']",
        "resume": "input[name='resume']",
        "submit_button": ".post-button",
    }
    
    async def navigate(self, page: Page, url: str):
        await WorkflowPrimitives.navigate_with_retry(page, url, "Lever")

    async def fill_personal_info(self, page: Page, profile: Dict[str, Any]):
        # Lever uses different patterns (often name-based)
        mappings = {
            "input[name='name']": f"{profile.get('first_name')} {profile.get('last_name')}",
            "input[name='email']": profile.get("email"),
            "input[name='phone']": profile.get("phone"),
        }
        
        for selector, value in mappings.items():
            if value:
                await WorkflowPrimitives.fill_field(page, selector, value, "Lever")

    async def upload_resume(self, page: Page, resume_path: str):
        await WorkflowPrimitives.upload_file(page, "input[name='resume']", resume_path, "Lever")

    async def handle_custom_questions(self, page: Page, ai_answers: Dict[str, str]):
        # Lever custom questions often use application-question classes
        pass

    async def submit(self, page: Page) -> bool:
        try:
            # Lever often has a 'submit' or 'apply' button at the bottom
            await WorkflowPrimitives.click_button(page, self.selector_catalog["submit_button"], "Lever")
            return True
        except Exception:
            self.log_selector_failure("submit_button", "Lever")
            return False
