"""URL constants for Rosetta Stone application."""

from dataclasses import dataclass


@dataclass(frozen=True)
class URLs:
    """
    URLs for Rosetta Stone application pages.
    
    Centralized URL management for easy maintenance.
    """
    
    # Authentication
    LOGIN: str = "https://login.rosettastone.com/login"
    LAUNCHPAD: str = "https://login.rosettastone.com/launchpad"

    # Content
    STORIES: str = "https://totale.rosettastone.com/stories"

    # Totale app origin (used as Referer/Origin for the usage API)
    TOTALE_ORIGIN: str = "https://totale.rosettastone.com"
    TOTALE_REFERER: str = "https://totale.rosettastone.com/"

    # Stories usage reporting API (LCP)
    LCP_BASE: str = "https://lcp.rosettastone.com"
    REPORT_USAGE: str = "https://lcp.rosettastone.com/api/v3/app_usage/report_usage"
    REPORT_ADDITIONAL_USAGE: str = (
        "https://lcp.rosettastone.com/api/v3/app_usage/report_additional_usage"
    )

    # Learner dashboard (hours readback)
    DASHBOARD_BASE: str = "https://prism.rosettastone.com/reports/learner/dashboard"
