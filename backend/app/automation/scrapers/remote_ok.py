import httpx
from typing import List
from app.automation.scrapers.base import BaseScraper
from app.automation.scrapers.search_filter import matches_search_query
from app.schemas.job import JobCreate
from app.core.logging import logger


class RemoteOKScraper(BaseScraper):
    def __init__(self, search_query: str = "Software Engineer", max_jobs: int = 40):
        self.search_query = search_query
        self.max_jobs = max_jobs

    @property
    def source_name(self) -> str:
        return "RemoteOK"

    async def scrape(self) -> List[JobCreate]:
        url = "https://remoteok.com/api"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        logger.info(f"Starting scrape from {self.source_name}...")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            logger.error(f"Failed to fetch data from RemoteOK: {e}")
            return []

        jobs = []
        # RemoteOK API returns metadata as the first element
        for item in data[1:]:
            try:
                if not matches_search_query(
                    self.search_query,
                    (
                        item.get("position"),
                        item.get("description"),
                        " ".join(item.get("tags") or []),
                    ),
                ):
                    continue

                job = JobCreate(
                    source_id=f"RemoteOK:{item.get('id') or item.get('url')}",
                    title=item.get("position"),
                    company=item.get("company"),
                    location=item.get("location") or "Remote",
                    description=item.get("description"),
                    salary=f"{item.get('salary_min', '')}-{item.get('salary_max', '')} {item.get('currency', '')}".strip(),
                    url=item.get("url"),
                    source=self.source_name,
                    remote_type="Remote",
                    raw_data=item,
                )
                jobs.append(job)
                if len(jobs) >= self.max_jobs:
                    break
            except Exception as e:
                logger.warning(f"Failed to parse job item from RemoteOK: {e}")
                continue

        logger.info(f"Successfully scraped {len(jobs)} jobs from {self.source_name}")
        return jobs
