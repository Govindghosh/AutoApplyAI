from playwright.async_api import Page
from typing import Dict, Any, Optional
from app.core.logging import logger
from app.services.health_service import HealthService

class WorkflowPrimitives:
    """
    Library of reusable orchestration primitives to reduce duplication
    and ensure consistent execution across all ATS adapters.
    """
    
    @staticmethod
    async def navigate_with_retry(page: Page, url: str, platform: str):
        logger.info(f"Primitive: Navigating to {url}")
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            HealthService.record_success(platform, "navigation")
        except Exception as e:
            HealthService.record_failure(platform, "navigation")
            raise e

    @staticmethod
    async def fill_field(page: Page, selector: str, value: str, platform: str):
        try:
            await page.wait_for_selector(selector, timeout=5000)
            await page.fill(selector, value)
            HealthService.record_success(platform, selector)
        except Exception:
            HealthService.record_failure(platform, selector)
            # We don't raise here to allow the workflow to attempt other fields
            logger.warning(f"Failed to fill field {selector} on {platform}")

    @staticmethod
    async def upload_file(page: Page, selector: str, file_path: str, platform: str):
        try:
            await page.set_input_files(selector, file_path)
            HealthService.record_success(platform, "file_upload")
        except Exception as e:
            HealthService.record_failure(platform, "file_upload")
            raise e

    @staticmethod
    async def click_button(page: Page, selector: str, platform: str):
        try:
            await page.click(selector)
            HealthService.record_success(platform, "button_click")
        except Exception as e:
            HealthService.record_failure(platform, "button_click")
            raise e
