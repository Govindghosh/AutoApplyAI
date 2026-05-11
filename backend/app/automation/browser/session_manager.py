import os
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from app.core.logging import logger

STORAGE_DIR = Path("storage/sessions")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

class SessionManager:
    @staticmethod
    def get_session_path(platform: str, user_id: int) -> Path:
        platform_key = platform.strip().lower()
        return STORAGE_DIR / f"user_{user_id}_{platform_key}.json"

    @staticmethod
    async def save_session(platform: str, user_id: int):
        """
        Launches a browser for the user to manually log in, then saves the storage state.
        This is a 'Human-in-the-loop' step for initial session creation.
        """
        session_path = SessionManager.get_session_path(platform, user_id)
        
        async with async_playwright() as p:
            # Launch in non-headless mode for manual login
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            logger.info(f"Please log in to {platform} in the opened browser...")
            
            # We wait for the user to finish login. 
            # In a real production app, this would be handled differently (e.g., remote browser).
            # For local dev, we can wait for a specific signal or just keep it open.
            await page.goto(SessionManager.get_platform_url(platform))
            
            # Wait for user to manually close the browser after login
            # or we can wait for a timeout.
            await page.wait_for_timeout(60000) # 60 seconds for manual login
            
            await context.storage_state(path=str(session_path))
            await browser.close()
            
            logger.info(f"Session saved for {platform} at {session_path}")

    @staticmethod
    def get_platform_url(platform: str) -> str:
        urls = {
            "wellfound": "https://wellfound.com/login",
            "linkedin": "https://www.linkedin.com/login",
            "remoteok": "https://remoteok.com",
            "indeed": "https://in.indeed.com",
            "glassdoor": "https://www.glassdoor.co.in",
            "naukri": "https://www.naukri.com",
            "workindia": "https://www.workindia.in",
            "foundit": "https://www.foundit.in",
            "shine": "https://www.shine.com",
            "timesjobs": "https://www.timesjobs.com",
            "cutshort": "https://cutshort.io",
        }
        return urls.get(platform.lower(), "https://google.com")

    @staticmethod
    async def get_browser_context(p, platform: str, user_id: int, headless: bool = True):
        """
        Returns a browser context with the saved session.
        Includes automated retry logic for stability.
        """
        session_path = SessionManager.get_session_path(platform, user_id)
        
        for attempt in range(3):
            try:
                browser = await p.chromium.launch(
                    headless=headless,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
                
                if session_path.exists():
                    logger.debug(f"Loading session: {platform}")
                    return await browser.new_context(
                        storage_state=str(session_path),
                        viewport={"width": 1366, "height": 900},
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                    )
                return await browser.new_context(
                    viewport={"width": 1366, "height": 900},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
            except Exception as e:
                logger.error(f"Browser launch attempt {attempt+1} failed: {e}")
                if attempt == 2: raise e
                await asyncio.sleep(2)

    @staticmethod
    def cleanup_stale_processes():
        """
        Aggressively kills orphaned Chromium/Playwright processes.
        Operational hardening for long-running servers.
        """
        import psutil
        count = 0
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                    proc.kill()
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if count > 0:
            logger.info(f"Cleaned up {count} orphaned browser processes")
