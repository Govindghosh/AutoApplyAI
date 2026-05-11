import re
from urllib.parse import urlencode

from app.automation.scrapers.browser_job_board import BrowserJobBoardConfig, BrowserJobBoardScraper


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "jobs"


def _build_search_url(query: str, location: str) -> str:
    return "https://www.timesjobs.com/candidate/job-search.html?" + urlencode(
        {
            "searchType": "personalizedSearch",
            "from": "submit",
            "txtKeywords": query,
            "txtLocation": location,
            "sortBy": "lastPosted",
            "luceneResultSize": "25",
            "postWeek": "60",
        }
    )


class TimesJobsScraper(BrowserJobBoardScraper):
    def __init__(
        self,
        search_query: str = "Software Engineer",
        location: str = "Remote",
        max_jobs: int = 25,
        session_user_id: int = 1,
    ):
        super().__init__(
            BrowserJobBoardConfig(
                source_name="TimesJobs",
                base_url="https://www.timesjobs.com",
                build_search_url=_build_search_url,
                card_selectors=(
                    "li.clearfix.job-bx",
                    "li[class*='job-bx']",
                    "ul.new-joblist li",
                    "article",
                ),
                title_selectors=(
                    "h2 a",
                    "h3 a",
                    "a[href*='/job-detail/']",
                ),
                company_selectors=(
                    "h3.joblist-comp-name",
                    "[class*='comp-name']",
                    "[class*='company']",
                ),
                location_selectors=(
                    "ul.top-jd-dtl li span",
                    "[class*='location']",
                    "[class*='loc']",
                ),
                salary_selectors=(
                    "[class*='salary']",
                    "[class*='package']",
                ),
                description_selectors=(
                    "ul.list-job-dtl",
                    ".job-description__",
                    "[class*='description']",
                    "p",
                ),
                link_selectors=(
                    "h2 a",
                    "h3 a",
                    "a[href*='/job-detail/']",
                ),
            ),
            search_query=search_query,
            location=location,
            max_jobs=max_jobs,
            session_user_id=session_user_id,
        )
