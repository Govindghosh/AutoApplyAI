from urllib.parse import urlencode

from app.automation.scrapers.browser_job_board import BrowserJobBoardConfig, BrowserJobBoardScraper


def _build_search_url(query: str, location: str) -> str:
    return "https://www.workindia.in/jobs/?" + urlencode(
        {
            "search": query,
            "location": location,
        }
    )


class WorkIndiaScraper(BrowserJobBoardScraper):
    def __init__(
        self,
        search_query: str = "Software Engineer",
        location: str = "Remote",
        max_jobs: int = 25,
        session_user_id: int = 1,
    ):
        super().__init__(
            BrowserJobBoardConfig(
                source_name="WorkIndia",
                base_url="https://www.workindia.in",
                build_search_url=_build_search_url,
                card_selectors=(
                    "[data-testid*='job']",
                    "article",
                    "li[class*='job']",
                    "div[class*='job-card']",
                    "div[class*='JobCard']",
                ),
                title_selectors=(
                    "h1",
                    "h2",
                    "h3",
                    "a[href*='/job/']",
                    "a[href*='/jobs/']",
                ),
                company_selectors=(
                    "[class*='company']",
                    "[class*='Company']",
                    "[data-testid*='company']",
                ),
                location_selectors=(
                    "[class*='location']",
                    "[class*='Location']",
                    "[data-testid*='location']",
                ),
                salary_selectors=(
                    "[class*='salary']",
                    "[class*='Salary']",
                    "[data-testid*='salary']",
                ),
                description_selectors=(
                    "[class*='description']",
                    "[class*='Description']",
                    "p",
                ),
                link_selectors=(
                    "a[href*='/job/']",
                    "a[href*='/jobs/']",
                ),
            ),
            search_query=search_query,
            location=location,
            max_jobs=max_jobs,
            session_user_id=session_user_id,
        )
