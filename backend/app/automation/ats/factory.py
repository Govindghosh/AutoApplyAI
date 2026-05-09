from app.automation.ats.base import ATSAdapter
from app.automation.ats.greenhouse import GreenhouseAdapter
from app.automation.ats.lever import LeverAdapter
from typing import Optional

class ATSFactory:
    @staticmethod
    def get_adapter(platform: str) -> Optional[ATSAdapter]:
        """
        Factory method to resolve the correct ATS driver based on platform signature.
        """
        p = platform.lower()
        if "greenhouse" in p:
            return GreenhouseAdapter()
        elif "lever" in p:
            return LeverAdapter()
        
        # Fallback to a generic adapter in the future
        return None
