import re

from app.automation.scrapers.browser_job_board import BrowserJobBoardConfig, BrowserJobBoardScraper


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "jobs"


def _build_search_url(query: str, location: str) -> str:
    base = f"https://www.shine.com/job-search/{_slug(query)}-jobs"
    if location and "remote" not in location.lower():
        return f"{base}-in-{_slug(location)}"
    return base


class ShineScraper(BrowserJobBoardScraper):
    def __init__(
        self,
        search_query: str = "Software Engineer",
        location: str = "Remote",
        max_jobs: int = 25,
        session_user_id: int = 1,
    ):
        super().__init__(
            BrowserJobBoardConfig(
                source_name="Shine",
                base_url="https://www.shine.com",
                build_search_url=_build_search_url,
                card_selectors=(
                    "div.jobCard",
                    "div[class*='jobCard']",
                    "li[class*='job']",
                    "article",
                ),
                title_selectors=(
                    "h2 a",
                    "h3 a",
                    "a[href*='/jobs/']",
                    "[class*='jobTitle']",
                    "[class*='title']",
                ),
                company_selectors=(
                    "[class*='company']",
                    "[class*='Company']",
                    "div[class*='recruiter']",
                ),
                location_selectors=(
                    "[class*='location']",
                    "[class*='Location']",
                    "[class*='loc']",
                ),
                salary_selectors=(
                    "[class*='salary']",
                    "[class*='Salary']",
                ),
                description_selectors=(
                    "[class*='description']",
                    "[class*='Description']",
                    "[class*='skill']",
                    "p",
                ),
                link_selectors=(
                    "h2 a",
                    "h3 a",
                    "a[href*='/jobs/']",
                    "a[href]",
                ),
            ),
            search_query=search_query,
            location=location,
            max_jobs=max_jobs,
            session_user_id=session_user_id,
        )
