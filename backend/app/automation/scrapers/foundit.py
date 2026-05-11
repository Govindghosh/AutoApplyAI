import re
from urllib.parse import urlencode

from app.automation.scrapers.browser_job_board import BrowserJobBoardConfig, BrowserJobBoardScraper


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "jobs"


def _build_search_url(query: str, location: str) -> str:
    return f"https://www.foundit.in/search/{_slug(query)}-jobs?" + urlencode(
        {
            "query": query,
            "locations": location,
        }
    )


class FounditScraper(BrowserJobBoardScraper):
    def __init__(
        self,
        search_query: str = "Software Engineer",
        location: str = "Remote",
        max_jobs: int = 25,
        session_user_id: int = 1,
    ):
        super().__init__(
            BrowserJobBoardConfig(
                source_name="Foundit",
                base_url="https://www.foundit.in",
                build_search_url=_build_search_url,
                card_selectors=(
                    "div.cardContainer",
                    "div[class*='jobCard']",
                    "section[class*='card']",
                    "div[class*='srpResultCard']",
                    "article",
                ),
                title_selectors=(
                    "a[href*='/job/']",
                    "h3",
                    "h2",
                    "[class*='jobTitle']",
                    "[class*='title']",
                ),
                company_selectors=(
                    "[class*='company']",
                    "[class*='Company']",
                    "span[class*='name']",
                ),
                location_selectors=(
                    "[class*='location']",
                    "[class*='Location']",
                    "[class*='loc']",
                ),
                salary_selectors=(
                    "[class*='salary']",
                    "[class*='Salary']",
                    "[class*='package']",
                ),
                description_selectors=(
                    "[class*='description']",
                    "[class*='Description']",
                    "[class*='skill']",
                    "p",
                ),
                link_selectors=(
                    "a[href*='/job/']",
                    "a[href*='/jobs/']",
                    "a[href]",
                ),
            ),
            search_query=search_query,
            location=location,
            max_jobs=max_jobs,
            session_user_id=session_user_id,
        )
