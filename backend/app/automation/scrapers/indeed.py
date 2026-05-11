from urllib.parse import urlencode

from app.automation.scrapers.browser_job_board import BrowserJobBoardConfig, BrowserJobBoardScraper


def _build_search_url(query: str, location: str) -> str:
    return "https://in.indeed.com/jobs?" + urlencode(
        {
            "q": query,
            "l": location,
            "sort": "date",
        }
    )


class IndeedScraper(BrowserJobBoardScraper):
    def __init__(
        self,
        search_query: str = "Software Engineer",
        location: str = "Remote",
        max_jobs: int = 25,
        session_user_id: int = 1,
    ):
        super().__init__(
            BrowserJobBoardConfig(
                source_name="Indeed",
                base_url="https://in.indeed.com",
                build_search_url=_build_search_url,
                card_selectors=(
                    "div.job_seen_beacon",
                    "div.cardOutline",
                    "td.resultContent",
                ),
                title_selectors=(
                    "a.jcs-JobTitle span",
                    "a.jcs-JobTitle",
                    "h2.jobTitle span",
                    "h2 a",
                ),
                company_selectors=(
                    "[data-testid='company-name']",
                    "span.companyName",
                    ".companyName",
                ),
                location_selectors=(
                    "[data-testid='text-location']",
                    "div.companyLocation",
                    ".companyLocation",
                ),
                salary_selectors=(
                    "[data-testid='attribute_snippet_testid']",
                    ".salary-snippet-container",
                    ".metadata.salary-snippet-container",
                ),
                description_selectors=(
                    ".job-snippet",
                    "ul",
                ),
                link_selectors=(
                    "a.jcs-JobTitle",
                    "h2 a",
                    "a[href*='/viewjob']",
                ),
            ),
            search_query=search_query,
            location=location,
            max_jobs=max_jobs,
            session_user_id=session_user_id,
        )
