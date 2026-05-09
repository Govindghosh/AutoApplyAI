from typing import List, Dict, Any
from app.automation.scrapers.base import BaseScraper
from app.core.logging import logger
from app.automation.browser.session_manager import SessionManager
from playwright.async_api import async_playwright
import asyncio

class WellfoundScraper(BaseScraper):
    def __init__(self):
        self.source = "Wellfound"
        self.base_url = "https://www.wellfound.com/jobs"

    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrapes startup jobs from Wellfound using Playwright.
        """
        logger.info(f"Starting Wellfound scrape...")
        jobs = []
        
        async with async_playwright() as p:
            # Note: Wellfound is very aggressive with bot detection.
            # We use a persistent context with realistic headers.
            context = await SessionManager.get_browser_context(p, self.source, 1, headless=True)
            page = await context.new_page()
            
            try:
                # Navigate to jobs page
                # We target specific search params for better results
                search_url = f"{self.base_url}?role=Software+Engineer&location=Remote"
                await page.goto(search_url, wait_until="networkidle", timeout=60000)
                
                # Wait for job cards to load
                await page.wait_for_selector("[data-test='JobResultCard']", timeout=15000)
                
                cards = await page.query_selector_all("[data-test='JobResultCard']")
                logger.info(f"Found {len(cards)} job cards on Wellfound")
                
                for card in cards[:15]: # Limit to first 15 for stability
                    try:
                        title_el = await card.query_selector("h2")
                        company_el = await card.query_selector("h3")
                        link_el = await card.query_selector("a[data-test='JobTitleLink']")
                        
                        if title_el and link_el:
                            title = await title_el.inner_text()
                            company = await company_el.inner_text() if company_el else "Unknown Startup"
                            url = await link_el.get_attribute("href")
                            if url and not url.startswith("http"):
                                url = f"https://wellfound.com{url}"
                            
                            # Extract description placeholder (full extraction happens during analysis)
                            desc_snippet = await card.inner_text()
                            
                            jobs.append({
                                "title": title.strip(),
                                "company": company.strip(),
                                "url": url,
                                "description": desc_snippet,
                                "source": self.source,
                                "location": "Remote",
                                "salary_range": "Competitive" # Wellfound often hides salary behind login
                            })
                    except Exception as e:
                        logger.warning(f"Failed to parse Wellfound card: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Wellfound scraping failed: {e}")
                # This is where Telemetry would broadcast a failure event
                from app.services.event_service import EventService, EventType
                EventService.emit(1, EventType.SYSTEM_ALERT, {"message": f"Wellfound Scraper blocked: {str(e)}", "severity": "warning"})
            finally:
                await context.close()
                
        return jobs
