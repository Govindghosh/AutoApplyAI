import re
from urllib.parse import urlencode

import httpx

from app.automation.scrapers.base import BaseScraper
from app.automation.scrapers.search_filter import matches_search_query
from app.core.logging import logger
from app.schemas.job import JobCreate


class RemotiveScraper(BaseScraper):
    def __init__(self, search_query: str = "Software Engineer", max_jobs: int = 25):
        self.search_query = search_query
        self.max_jobs = max_jobs

    @property
    def source_name(self) -> str:
        return "Remotive"

    async def scrape(self) -> list[JobCreate]:
        url = "https://remotive.com/api/remote-jobs?" + urlencode({"search": self.search_query})
        logger.info(f"Starting scrape from {self.source_name}: {url}")

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "AutoApplyAI/1.0"})
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.error(f"Failed to fetch data from Remotive: {exc}")
            return []

        jobs: list[JobCreate] = []
        for item in data.get("jobs", [])[: self.max_jobs]:
            try:
                title = item.get("title")
                company = item.get("company_name")
                job_url = item.get("url")
                if not title or not company or not job_url:
                    continue

                description = re.sub(r"<[^>]+>", " ", item.get("description") or "")
                if not matches_search_query(
                    self.search_query,
                    (title, company, description, item.get("category")),
                ):
                    continue

                jobs.append(
                    JobCreate(
                        source_id=f"Remotive:{item.get('id') or job_url}",
                        title=title,
                        company=company,
                        location=item.get("candidate_required_location") or "Remote",
                        description=description,
                        salary=item.get("salary"),
                        url=job_url,
                        source=self.source_name,
                        remote_type="Remote",
                        raw_data=item,
                    )
                )
            except Exception as exc:
                logger.warning(f"Failed to parse Remotive job item: {exc}")

        logger.info(f"Successfully scraped {len(jobs)} jobs from {self.source_name}")
        return jobs
