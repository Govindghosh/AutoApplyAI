from urllib.parse import urlencode

from app.automation.scrapers.browser_job_board import BrowserJobBoardConfig, BrowserJobBoardScraper


def _build_search_url(query: str, location: str) -> str:
    params = {
        "keywords": query,
        "location": location,
        "sortBy": "DD",
    }
    if "remote" in location.lower():
        params["f_WT"] = "2"
    return "https://www.linkedin.com/jobs/search/?" + urlencode(params)


class LinkedInScraper(BrowserJobBoardScraper):
    def __init__(
        self,
        search_query: str = "Software Engineer",
        location: str = "Remote",
        max_jobs: int = 25,
        session_user_id: int = 1,
    ):
        super().__init__(
            BrowserJobBoardConfig(
                source_name="LinkedIn",
                base_url="https://www.linkedin.com",
                build_search_url=_build_search_url,
                card_selectors=(
                    "li.jobs-search-results__list-item",
                    "div.job-card-container",
                    "div.base-search-card",
                    "li[data-occludable-job-id]",
                ),
                title_selectors=(
                    "a.job-card-list__title--link",
                    "a.job-card-container__link",
                    "h3.base-search-card__title",
                    "a[href*='/jobs/view/']",
                ),
                company_selectors=(
                    ".job-card-container__primary-description",
                    "h4.base-search-card__subtitle",
                    ".base-search-card__subtitle",
                ),
                location_selectors=(
                    ".job-card-container__metadata-item",
                    ".job-search-card__location",
                    ".base-search-card__metadata",
                ),
                salary_selectors=(
                    ".job-card-container__metadata-item--salary-info",
                    ".salary",
                ),
                description_selectors=(
                    ".job-card-list__footer-wrapper",
                    ".base-search-card__metadata",
                    ".job-card-container__metadata-wrapper",
                ),
                link_selectors=(
                    "a.job-card-list__title--link",
                    "a.job-card-container__link",
                    "a.base-card__full-link",
                    "a[href*='/jobs/view/']",
                ),
            ),
            search_query=search_query,
            location=location,
            max_jobs=max_jobs,
            session_user_id=session_user_id,
        )
