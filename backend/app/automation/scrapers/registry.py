from dataclasses import dataclass
from typing import Callable

from app.automation.scrapers.arbeitnow import ArbeitnowScraper
from app.automation.scrapers.base import BaseScraper
from app.automation.scrapers.cutshort import CutShortScraper
from app.automation.scrapers.foundit import FounditScraper
from app.automation.scrapers.glassdoor import GlassdoorScraper
from app.automation.scrapers.indeed import IndeedScraper
from app.automation.scrapers.jobicy import JobicyScraper
from app.automation.scrapers.linkedin import LinkedInScraper
from app.automation.scrapers.naukri import NaukriScraper
from app.automation.scrapers.remote_ok import RemoteOKScraper
from app.automation.scrapers.remotive import RemotiveScraper
from app.automation.scrapers.shine import ShineScraper
from app.automation.scrapers.timesjobs import TimesJobsScraper
from app.automation.scrapers.wellfound import WellfoundScraper
from app.automation.scrapers.workindia import WorkIndiaScraper

ScraperFactory = Callable[[str, str, int], BaseScraper]


@dataclass(frozen=True)
class ScraperDefinition:
    source_name: str
    factory: ScraperFactory


SUPPORTED_SCRAPERS: tuple[ScraperDefinition, ...] = (
    ScraperDefinition(
        "Remotive",
        lambda query, _location, _user_id: RemotiveScraper(search_query=query),
    ),
    ScraperDefinition(
        "Jobicy", lambda query, _location, _user_id: JobicyScraper(search_query=query)
    ),
    ScraperDefinition(
        "Arbeitnow",
        lambda query, _location, _user_id: ArbeitnowScraper(search_query=query),
    ),
    ScraperDefinition(
        "RemoteOK",
        lambda query, _location, _user_id: RemoteOKScraper(search_query=query),
    ),
    ScraperDefinition(
        "Wellfound",
        lambda query, location, user_id: WellfoundScraper(
            search_query=query,
            location=location,
            session_user_id=user_id,
        ),
    ),
    ScraperDefinition(
        "LinkedIn",
        lambda query, location, user_id: LinkedInScraper(
            search_query=query,
            location=location,
            session_user_id=user_id,
        ),
    ),
    ScraperDefinition(
        "Indeed",
        lambda query, location, user_id: IndeedScraper(
            search_query=query,
            location=location,
            session_user_id=user_id,
        ),
    ),
    ScraperDefinition(
        "Glassdoor",
        lambda query, location, user_id: GlassdoorScraper(
            search_query=query,
            location=location,
            session_user_id=user_id,
        ),
    ),
    ScraperDefinition(
        "Naukri",
        lambda query, location, user_id: NaukriScraper(
            search_query=query,
            location=location,
            session_user_id=user_id,
        ),
    ),
    ScraperDefinition(
        "Foundit",
        lambda query, location, user_id: FounditScraper(
            search_query=query,
            location=location,
            session_user_id=user_id,
        ),
    ),
    ScraperDefinition(
        "Shine",
        lambda query, location, user_id: ShineScraper(
            search_query=query,
            location=location,
            session_user_id=user_id,
        ),
    ),
    ScraperDefinition(
        "TimesJobs",
        lambda query, location, user_id: TimesJobsScraper(
            search_query=query,
            location=location,
            session_user_id=user_id,
        ),
    ),
    ScraperDefinition(
        "CutShort",
        lambda query, location, user_id: CutShortScraper(
            search_query=query,
            location=location,
            session_user_id=user_id,
        ),
    ),
    ScraperDefinition(
        "WorkIndia",
        lambda query, location, user_id: WorkIndiaScraper(
            search_query=query,
            location=location,
            session_user_id=user_id,
        ),
    ),
)


def build_scrapers(
    search_query: str, search_location: str, session_user_id: int
) -> list[BaseScraper]:
    return [
        definition.factory(search_query, search_location, session_user_id)
        for definition in SUPPORTED_SCRAPERS
    ]


def supported_source_names() -> list[str]:
    return [definition.source_name for definition in SUPPORTED_SCRAPERS]
