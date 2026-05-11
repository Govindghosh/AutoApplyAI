import re

import httpx

from app.automation.scrapers.base import BaseScraper
from app.automation.scrapers.search_filter import matches_search_query
from app.core.logging import logger
from app.schemas.job import JobCreate


class ArbeitnowScraper(BaseScraper):
    def __init__(self, search_query: str = "Software Engineer", max_jobs: int = 25):
        self.search_query = search_query
        self.max_jobs = max_jobs

    @property
    def source_name(self) -> str:
        return "Arbeitnow"

    async def scrape(self) -> list[JobCreate]:
        url = "https://www.arbeitnow.com/api/job-board-api"
        logger.info(f"Starting scrape from {self.source_name}: {url}")

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "AutoApplyAI/1.0"})
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.error(f"Failed to fetch data from Arbeitnow: {exc}")
            return []

        jobs: list[JobCreate] = []
        for item in data.get("data", []):
            try:
                title = item.get("title")
                job_url = item.get("url")
                if not title or not job_url:
                    continue

                if not matches_search_query(
                    self.search_query,
                    (
                        item.get("title"),
                        item.get("description"),
                        " ".join(item.get("tags") or []),
                    ),
                ):
                    continue

                description = re.sub(r"<[^>]+>", " ", item.get("description") or "")
                jobs.append(
                    JobCreate(
                        source_id=f"Arbeitnow:{item.get('slug') or item.get('url')}",
                        title=item.get("title"),
                        company=item.get("company_name") or "Unknown",
                        location=item.get("location") or "Remote",
                        description=description,
                        salary=None,
                        url=item.get("url"),
                        source=self.source_name,
                        remote_type="Remote" if item.get("remote") else None,
                        raw_data=item,
                    )
                )
                if len(jobs) >= self.max_jobs:
                    break
            except Exception as exc:
                logger.warning(f"Failed to parse Arbeitnow job item: {exc}")

        logger.info(f"Successfully scraped {len(jobs)} jobs from {self.source_name}")
        return jobs
