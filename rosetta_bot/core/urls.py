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
