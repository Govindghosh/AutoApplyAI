from app.automation.ats.base import ATSAdapter
from app.automation.ats.greenhouse import GreenhouseAdapter
from app.automation.ats.lever import LeverAdapter
from app.automation.ats.selective_expansion import (
    AshbyAdapter,
    ICIMSAdapter,
    SmartRecruitersAdapter,
    TaleoAdapter,
    WorkdayAdapter,
)
from typing import Optional

class ATSFactory:
    ADAPTERS = {
        "greenhouse": GreenhouseAdapter,
        "lever": LeverAdapter,
        "ashby": AshbyAdapter,
        "workday": WorkdayAdapter,
        "smartrecruiters": SmartRecruitersAdapter,
        "smart recruiters": SmartRecruitersAdapter,
        "icims": ICIMSAdapter,
        "taleo": TaleoAdapter,
    }

    @staticmethod
    def get_adapter(platform: str) -> Optional[ATSAdapter]:
        """
        Factory method to resolve the correct ATS driver based on platform signature.
        """
        p = platform.lower()
        for signature, adapter_cls in ATSFactory.ADAPTERS.items():
            if signature in p:
                return adapter_cls()
        
        # Fallback to a generic adapter in the future
        return None
