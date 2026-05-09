from abc import ABC, abstractmethod
from typing import List
from app.schemas.job import JobCreate

class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self) -> List[JobCreate]:
        """
        Scrape jobs from the source and return a list of JobCreate objects.
        """
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        Return the name of the source (e.g., 'RemoteOK').
        """
        pass
