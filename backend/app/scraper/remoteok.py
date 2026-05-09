import asyncio
from bs4 import BeautifulSoup
from app.scraper.base import BaseScraper
from app.schemas.job import JobCreate
from app.core.logging import logger

class RemoteOKScraper(BaseScraper):
    BASE_URL = "https://remoteok.com"

    async def scrape_jobs(self):
        html = await self.get_page_content(self.BASE_URL)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        job_listings = []
        
        # RemoteOK uses 'tr' with class 'job'
        rows = soup.find_all("tr", class_="job")
        
        for row in rows:
            try:
                title = row.find("h2", itemprop="title").get_text(strip=True)
                company = row.find("h3", itemprop="name").get_text(strip=True)
                url = self.BASE_URL + row.find("a", class_="preventLink")["href"]
                
                # Tags for location/salary
                tags = row.find_all("div", class_="tag")
                location = tags[0].get_text(strip=True) if tags else "Remote"
                
                job_listings.append(JobCreate(
                    title=title,
                    company=company,
                    url=url,
                    location=location,
                    source="RemoteOK",
                    remote_type="Remote"
                ))
            except Exception as e:
                logger.warning(f"Failed to parse a job row: {str(e)}")
                continue
        
        logger.info(f"Scraped {len(job_listings)} jobs from RemoteOK")
        return job_listings
