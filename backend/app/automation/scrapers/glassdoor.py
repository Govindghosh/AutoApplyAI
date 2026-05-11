from urllib.parse import urlencode

from app.automation.scrapers.browser_job_board import BrowserJobBoardConfig, BrowserJobBoardScraper


def _build_search_url(query: str, location: str) -> str:
    params = {"sc.keyword": query}
    if location:
        params["locKeyword"] = location
    return "https://www.glassdoor.co.in/Job/jobs.htm?" + urlencode(params)


class GlassdoorScraper(BrowserJobBoardScraper):
    def __init__(
        self,
        search_query: str = "Software Engineer",
        location: str = "Remote",
        max_jobs: int = 25,
        session_user_id: int = 1,
    ):
        super().__init__(
            BrowserJobBoardConfig(
                source_name="Glassdoor",
                base_url="https://www.glassdoor.co.in",
                build_search_url=_build_search_url,
                card_selectors=(
                    "[data-test='jobListing']",
                    "li[data-test='jobListing']",
                    "li[class*='JobsList_jobListItem']",
                    "div[class*='JobCard']",
                ),
                title_selectors=(
                    "[data-test='job-title']",
                    "a[data-test='job-link']",
                    "a[class*='JobCard_jobTitle']",
                    "a[href*='/job-listing/']",
                ),
                company_selectors=(
                    "[data-test='employer-name']",
                    "[class*='EmployerProfile_compactEmployerName']",
                    "span[class*='employerName']",
                ),
                location_selectors=(
                    "[data-test='job-location']",
                    "[class*='JobCard_location']",
                ),
                salary_selectors=(
                    "[data-test='detailSalary']",
                    "[class*='salaryEstimate']",
                    "[class*='JobCard_salaryEstimate']",
                ),
                description_selectors=(
                    "[data-test='descSnippet']",
                    "[class*='JobCard_jobDescriptionSnippet']",
                    "[class*='jobDescriptionSnippet']",
                ),
                link_selectors=(
                    "a[data-test='job-link']",
                    "a[class*='JobCard_jobTitle']",
                    "a[href*='/job-listing/']",
                ),
            ),
            search_query=search_query,
            location=location,
            max_jobs=max_jobs,
            session_user_id=session_user_id,
        )
