from typing import Dict, Any
from playwright.async_api import Page
from app.core.logging import logger

class FormHandler:
    """
    Handles detection and filling of common job application form fields.
    """
    
    FIELD_MAPPING = {
        "full_name": ["name", "full_name", "fullName", "first_name", "last_name"],
        "email": ["email", "email_address", "user_email"],
        "phone": ["phone", "mobile", "contact_number", "telephone"],
        "resume": ["resume", "cv", "upload_resume", "file"],
        "linkedin": ["linkedin", "linkedin_url"],
        "portfolio": ["portfolio", "website", "github"],
    }

    @staticmethod
    async def fill_form(page: Page, profile_data: Dict[str, Any], resume_path: str):
        """
        Heuristic-based form filling.
        """
        logger.info("Starting heuristic form filling...")
        
        # This is a simplified version. A real implementation would use 
        # LLM-based field detection for complex forms.
        
        for field, keywords in FormHandler.FIELD_MAPPING.items():
            for keyword in keywords:
                try:
                    # Look for input fields with matching names, ids, or labels
                    selector = f'input[name*="{keyword}" i], input[id*="{keyword}" i], input[placeholder*="{keyword}" i]'
                    element = await page.query_selector(selector)
                    
                    if element and await element.is_visible():
                        if field == "resume":
                            await element.set_input_files(resume_path)
                            logger.info(f"Filled {field} using keyword {keyword}")
                        else:
                            val = profile_data.get(field)
                            if val:
                                await element.fill(str(val))
                                logger.info(f"Filled {field} with {val} using keyword {keyword}")
                        break # Move to next field after first match
                except Exception as e:
                    logger.warning(f"Failed to fill field {field} with keyword {keyword}: {e}")
                    continue

    @staticmethod
    async def detect_submit_button(page: Page):
        """
        Detects common submit buttons.
        """
        selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Apply")',
            'button:has-text("Submit Application")',
            'button:has-text("Next")'
        ]
        
        for selector in selectors:
            btn = await page.query_selector(selector)
            if btn and await btn.is_visible():
                return btn
        return None
