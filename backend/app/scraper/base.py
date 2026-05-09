import asyncio
from playwright.async_api import async_playwright
from app.core.config import settings
from app.core.logging import logger

class BaseScraper:
    def __init__(self):
        self.headless = settings.PLAYWRIGHT_HEADLESS

    async def get_page_content(self, url: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                logger.info(f"Navigating to {url}")
                await page.goto(url, wait_until="networkidle", timeout=60000)
                content = await page.content()
                return content
            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                return None
            finally:
                await browser.close()
