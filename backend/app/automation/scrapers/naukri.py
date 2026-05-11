import re
from urllib.parse import urlencode

from app.automation.scrapers.browser_job_board import BrowserJobBoardConfig, BrowserJobBoardScraper


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "jobs"


def _build_search_url(query: str, location: str) -> str:
    return f"https://www.naukri.com/{_slug(query)}-jobs?" + urlencode(
        {
            "k": query,
            "l": location,
            "sort": "dd",
        }
    )


class NaukriScraper(BrowserJobBoardScraper):
    def __init__(
        self,
        search_query: str = "Software Engineer",
        location: str = "Remote",
        max_jobs: int = 25,
        session_user_id: int = 1,
    ):
        super().__init__(
            BrowserJobBoardConfig(
                source_name="Naukri",
                base_url="https://www.naukri.com",
                build_search_url=_build_search_url,
                card_selectors=(
                    ".srp-jobtuple-wrapper",
                    "article.jobTuple",
                    ".jobTuple",
                    "div[class*='jobTuple']",
                ),
                title_selectors=(
                    "a.title",
                    "a[class*='title']",
                    "a[href*='/job-listings-']",
                ),
                company_selectors=(
                    "a.comp-name",
                    "a[class*='comp-name']",
                    ".companyInfo .subTitle",
                    "[class*='company']",
                ),
                location_selectors=(
                    ".locWdth",
                    ".location",
                    "[class*='loc']",
                ),
                salary_selectors=(
                    ".sal-wrap",
                    ".salary",
                    "[class*='sal']",
                ),
                description_selectors=(
                    ".job-desc",
                    ".job-description",
                    "[class*='job-desc']",
                ),
                link_selectors=(
                    "a.title",
                    "a[class*='title']",
                    "a[href*='/job-listings-']",
                ),
            ),
            search_query=search_query,
            location=location,
            max_jobs=max_jobs,
            session_user_id=session_user_id,
        )
