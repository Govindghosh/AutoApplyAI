from typing import Any, Dict

from playwright.async_api import Page

from app.automation.ats.base import ATSAdapter
from app.automation.workflow_primitives import WorkflowPrimitives


class GovernedSelectorAdapter(ATSAdapter):
    platform = "Generic"
    selector_catalog: Dict[str, str] = {
        "first_name": "input[name='first_name']",
        "last_name": "input[name='last_name']",
        "email": "input[type='email']",
        "phone": "input[type='tel']",
        "resume": "input[type='file']",
        "submit_button": "button[type='submit']",
    }

    async def navigate(self, page: Page, url: str):
        await WorkflowPrimitives.navigate_with_retry(page, url, self.platform)

    async def fill_personal_info(self, page: Page, profile: Dict[str, Any]):
        mappings = {
            self.selector_catalog["first_name"]: profile.get("first_name"),
            self.selector_catalog["last_name"]: profile.get("last_name"),
            self.selector_catalog["email"]: profile.get("email"),
            self.selector_catalog["phone"]: profile.get("phone"),
        }
        for selector, value in mappings.items():
            if value:
                await WorkflowPrimitives.fill_field(page, selector, value, self.platform)

    async def upload_resume(self, page: Page, resume_path: str):
        await WorkflowPrimitives.upload_file(page, self.selector_catalog["resume"], resume_path, self.platform)

    async def handle_custom_questions(self, page: Page, ai_answers: Dict[str, str]):
        return [
            {
                "question": question,
                "answer": answer,
                "resolution": "requires_human_review",
            }
            for question, answer in ai_answers.items()
        ]

    async def submit(self, page: Page) -> bool:
        try:
            await WorkflowPrimitives.click_button(page, self.selector_catalog["submit_button"], self.platform)
            return True
        except Exception:
            self.log_selector_failure("submit_button", self.platform)
            return False


class AshbyAdapter(GovernedSelectorAdapter):
    platform = "Ashby"
    selector_catalog = {
        "first_name": "input[name='firstName']",
        "last_name": "input[name='lastName']",
        "email": "input[name='email']",
        "phone": "input[name='phone']",
        "resume": "input[type='file']",
        "submit_button": "button[type='submit']",
    }


class WorkdayAdapter(GovernedSelectorAdapter):
    platform = "Workday"
    selector_catalog = {
        "first_name": "input[data-automation-id='legalNameSection_firstName']",
        "last_name": "input[data-automation-id='legalNameSection_lastName']",
        "email": "input[data-automation-id='email']",
        "phone": "input[data-automation-id='phone-number']",
        "resume": "input[type='file']",
        "submit_button": "button[data-automation-id='bottom-navigation-next-button']",
    }

    def capability_profile(self) -> Dict[str, Any]:
        profile = super().capability_profile()
        profile["governance_compatibility"]["requires_human_verification"] = True
        profile["recovery_semantics"]["checkpoint_replay_safe"] = True
        return profile


class SmartRecruitersAdapter(GovernedSelectorAdapter):
    platform = "SmartRecruiters"
    selector_catalog = {
        "first_name": "input[name='firstName']",
        "last_name": "input[name='lastName']",
        "email": "input[name='email']",
        "phone": "input[name='phoneNumber']",
        "resume": "input[type='file']",
        "submit_button": "button[type='submit']",
    }


class ICIMSAdapter(GovernedSelectorAdapter):
    platform = "iCIMS"
    selector_catalog = {
        "first_name": "input[name*='firstName']",
        "last_name": "input[name*='lastName']",
        "email": "input[name*='email']",
        "phone": "input[name*='phone']",
        "resume": "input[type='file']",
        "submit_button": "button[type='submit']",
    }

    def capability_profile(self) -> Dict[str, Any]:
        profile = super().capability_profile()
        profile["governance_compatibility"]["requires_human_verification"] = True
        return profile


class TaleoAdapter(GovernedSelectorAdapter):
    platform = "Taleo"
    selector_catalog = {
        "first_name": "input[name*='firstName']",
        "last_name": "input[name*='lastName']",
        "email": "input[name*='email']",
        "phone": "input[name*='phone']",
        "resume": "input[type='file']",
        "submit_button": "input[type='submit'], button[type='submit']",
    }

    def capability_profile(self) -> Dict[str, Any]:
        profile = super().capability_profile()
        profile["governance_compatibility"]["requires_human_verification"] = True
        profile["governance_compatibility"]["mandatory_human_verification"] = True
        return profile
