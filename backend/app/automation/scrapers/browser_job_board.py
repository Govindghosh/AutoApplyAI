import hashlib
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.automation.browser.session_manager import SessionManager
from app.automation.scrapers.base import BaseScraper
from app.core.config import settings
from app.core.logging import logger
from app.schemas.job import JobCreate


UrlBuilder = Callable[[str, str], str]


@dataclass(frozen=True)
class BrowserJobBoardConfig:
    source_name: str
    base_url: str
    build_search_url: UrlBuilder
    card_selectors: tuple[str, ...]
    title_selectors: tuple[str, ...]
    company_selectors: tuple[str, ...]
    location_selectors: tuple[str, ...]
    salary_selectors: tuple[str, ...]
    description_selectors: tuple[str, ...]
    link_selectors: tuple[str, ...]


class BrowserJobBoardScraper(BaseScraper):
    def __init__(
        self,
        config: BrowserJobBoardConfig,
        search_query: str = "Software Engineer",
        location: str = "Remote",
        max_jobs: int = 25,
        session_user_id: int = 1,
    ):
        self.config = config
        self.search_query = search_query
        self.location = location
        self.max_jobs = max_jobs
        self.session_user_id = session_user_id

    @property
    def source_name(self) -> str:
        return self.config.source_name

    async def scrape(self) -> list[JobCreate]:
        search_url = self.config.build_search_url(self.search_query, self.location)
        logger.info(f"Starting {self.source_name} scrape: {search_url}")

        async with async_playwright() as p:
            context = await SessionManager.get_browser_context(
                p,
                self.source_name,
                self.session_user_id,
                headless=settings.PLAYWRIGHT_HEADLESS,
            )
            page = await context.new_page()

            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except PlaywrightTimeoutError:
                    logger.debug(f"{self.source_name} did not reach networkidle; parsing loaded DOM")
                await self._warm_page(page)

                cards = await self._find_cards(page)
                jobs: list[JobCreate] = []

                for card in cards[: self.max_jobs]:
                    try:
                        title = await self._first_text(card, self.config.title_selectors)
                        link = await self._first_href(card, self.config.link_selectors)
                        if not title or not link:
                            continue

                        job_url = urljoin(self.config.base_url, link)
                        company = await self._first_text(card, self.config.company_selectors) or "Unknown"
                        location = await self._first_text(card, self.config.location_selectors) or self.location
                        salary = await self._first_text(card, self.config.salary_selectors)
                        description = (
                            await self._first_text(card, self.config.description_selectors)
                            or await card.inner_text()
                            or ""
                        )

                        jobs.append(
                            JobCreate(
                                source_id=self._source_id(job_url),
                                title=title,
                                company=company,
                                location=location,
                                description=description[:4000],
                                salary=salary,
                                url=job_url,
                                source=self.source_name,
                                remote_type="Remote" if "remote" in location.lower() else None,
                                raw_data={
                                    "search_query": self.search_query,
                                    "search_location": self.location,
                                    "search_url": search_url,
                                },
                            )
                        )
                    except Exception as exc:
                        logger.warning(f"Failed to parse {self.source_name} job card: {exc}")

                logger.info(f"Successfully scraped {len(jobs)} jobs from {self.source_name}")
                return jobs

            except Exception as exc:
                logger.error(f"{self.source_name} scraping failed: {exc}")
                return []
            finally:
                await context.close()

    async def _find_cards(self, page):
        for selector in self.config.card_selectors:
            cards = await page.query_selector_all(selector)
            if cards:
                return cards
        return []

    @staticmethod
    async def _warm_page(page):
        await page.wait_for_timeout(1500)
        for _ in range(2):
            await page.mouse.wheel(0, 1200)
            await page.wait_for_timeout(700)
        await page.mouse.wheel(0, -800)
        await page.wait_for_timeout(300)

    @staticmethod
    async def _first_text(root, selectors: tuple[str, ...]) -> str | None:
        for selector in selectors:
            element = root if await BrowserJobBoardScraper._matches(root, selector) else await root.query_selector(selector)
            if not element:
                continue
            text = (await element.inner_text() or "").strip()
            if text:
                return " ".join(text.split())
        return None

    @staticmethod
    async def _first_href(root, selectors: tuple[str, ...]) -> str | None:
        for selector in selectors:
            element = root if await BrowserJobBoardScraper._matches(root, selector) else await root.query_selector(selector)
            if not element:
                continue
            href = await element.get_attribute("href")
            if href:
                return href
        return None

    @staticmethod
    async def _matches(root, selector: str) -> bool:
        try:
            return bool(await root.evaluate("(el, selector) => el.matches(selector)", selector))
        except Exception:
            return False

    def _source_id(self, job_url: str) -> str:
        digest = hashlib.sha1(job_url.encode("utf-8")).hexdigest()
        return f"{self.source_name}:{digest}"
