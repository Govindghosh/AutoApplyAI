from app.automation.ats.base import ATSAdapter
from playwright.async_api import Page
from typing import Dict, Any
from app.core.logging import logger

class LeverAdapter(ATSAdapter):
    """
    High-fidelity automation driver for the Lever ATS platform.
    """
    
    async def navigate(self, page: Page, url: str):
        logger.info(f"Navigating to Lever job: {url}")
        await page.goto(url, wait_until="domcontentloaded")

    async def fill_personal_info(self, page: Page, profile: Dict[str, Any]):
        # Lever uses different patterns (often name-based)
        mappings = {
            "input[name='name']": f"{profile.get('first_name')} {profile.get('last_name')}",
            "input[name='email']": profile.get("email"),
            "input[name='phone']": profile.get("phone"),
        }
        
        for selector, value in mappings.items():
            if value:
                try:
                    await page.fill(selector, value)
                except Exception:
                    self.log_selector_failure(selector, "Lever")

    async def upload_resume(self, page: Page, resume_path: str):
        try:
            # Lever standard resume input
            await page.set_input_files("input[name='resume']", resume_path)
            logger.info("Resume uploaded to Lever successfully.")
        except Exception as e:
            self.log_selector_failure("resume_upload", "Lever")
            raise e

    async def handle_custom_questions(self, page: Page, ai_answers: Dict[str, str]):
        # Lever custom questions often use application-question classes
        pass

    async def submit(self, page: Page) -> bool:
        try:
            # Lever often has a 'submit' or 'apply' button at the bottom
            await page.click(".post-button")
            return True
        except Exception:
            self.log_selector_failure("submit_button", "Lever")
            return False
