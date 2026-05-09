import httpx
from typing import List
from app.automation.scrapers.base import BaseScraper
from app.schemas.job import JobCreate
from app.core.logging import logger

class RemoteOKScraper(BaseScraper):
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
                job = JobCreate(
                    source_id=str(item.get("id")),
                    title=item.get("position"),
                    company=item.get("company"),
                    location=item.get("location") or "Remote",
                    description=item.get("description"),
                    salary=f"{item.get('salary_min', '')}-{item.get('salary_max', '')} {item.get('currency', '')}".strip(),
                    url=item.get("url"),
                    source=self.source_name,
                    remote_type="Remote",
                    raw_data=item
                )
                jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to parse job item from RemoteOK: {e}")
                continue
        
        logger.info(f"Successfully scraped {len(jobs)} jobs from {self.source_name}")
        return jobs
