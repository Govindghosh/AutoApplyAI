import re

from app.automation.scrapers.browser_job_board import BrowserJobBoardConfig, BrowserJobBoardScraper


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "jobs"


def _build_search_url(query: str, location: str) -> str:
    if "remote" in location.lower():
        return "https://cutshort.io/collections/remote-jobs"
    return f"https://cutshort.io/jobs/{_slug(query)}-jobs-in-{_slug(location)}"


class CutShortScraper(BrowserJobBoardScraper):
    def __init__(
        self,
        search_query: str = "Software Engineer",
        location: str = "Remote",
        max_jobs: int = 25,
        session_user_id: int = 1,
    ):
        super().__init__(
            BrowserJobBoardConfig(
                source_name="CutShort",
                base_url="https://cutshort.io",
                build_search_url=_build_search_url,
                card_selectors=(
                    "div[class*='job-card']",
                    "div[class*='JobCard']",
                    "a[href*='/job/']",
                    "article",
                ),
                title_selectors=(
                    "h2",
                    "h3",
                    "a[href*='/job/']",
                    "[class*='title']",
                ),
                company_selectors=(
                    "[class*='company']",
                    "[class*='Company']",
                    "[class*='organization']",
                ),
                location_selectors=(
                    "[class*='location']",
                    "[class*='Location']",
                    "[class*='remote']",
                ),
                salary_selectors=(
                    "[class*='salary']",
                    "[class*='Salary']",
                    "[class*='compensation']",
                ),
                description_selectors=(
                    "[class*='description']",
                    "[class*='Description']",
                    "[class*='skill']",
                    "p",
                ),
                link_selectors=(
                    "a[href*='/job/']",
                    "a[href]",
                ),
            ),
            search_query=search_query,
            location=location,
            max_jobs=max_jobs,
            session_user_id=session_user_id,
        )
