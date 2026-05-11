import re

import httpx

from app.automation.scrapers.base import BaseScraper
from app.automation.scrapers.search_filter import matches_search_query
from app.core.logging import logger
from app.schemas.job import JobCreate


class JobicyScraper(BaseScraper):
    def __init__(self, search_query: str = "Software Engineer", max_jobs: int = 25):
        self.search_query = search_query
        self.max_jobs = max_jobs

    @property
    def source_name(self) -> str:
        return "Jobicy"

    async def scrape(self) -> list[JobCreate]:
        url = "https://jobicy.com/api/v2/remote-jobs"
        logger.info(f"Starting scrape from {self.source_name}: {url}")

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "AutoApplyAI/1.0"})
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.error(f"Failed to fetch data from Jobicy: {exc}")
            return []

        jobs: list[JobCreate] = []
        for item in data.get("jobs", []):
            try:
                title = item.get("jobTitle") or item.get("title")
                description = re.sub(r"<[^>]+>", " ", item.get("jobDescription") or item.get("jobExcerpt") or "")
                if not matches_search_query(
                    self.search_query,
                    (title, description, " ".join(item.get("jobIndustry") or [])),
                ):
                    continue

                job_url = item.get("url") or item.get("jobUrl")
                if not title or not job_url:
                    continue
                jobs.append(
                    JobCreate(
                        source_id=f"Jobicy:{item.get('id') or job_url}",
                        title=title,
                        company=item.get("companyName") or "Unknown",
                        location=item.get("jobGeo") or "Remote",
                        description=description,
                        salary=str(item.get("annualSalaryMin") or item.get("salary") or "") or None,
                        url=job_url,
                        source=self.source_name,
                        remote_type="Remote",
                        raw_data=item,
                    )
                )
                if len(jobs) >= self.max_jobs:
                    break
            except Exception as exc:
                logger.warning(f"Failed to parse Jobicy job item: {exc}")

        logger.info(f"Successfully scraped {len(jobs)} jobs from {self.source_name}")
        return jobs
