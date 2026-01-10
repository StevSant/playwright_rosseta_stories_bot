"""
Rosetta Stone Bot Package

A modular automation bot for Rosetta Stone language learning platform,
following a clean architecture with:
- Page Object Model (POM) for UI interactions
- Service Layer for reusable business logic
- Workflow Pattern for automation scenarios

Structure:
    - core/: Fundamental building blocks (constants, logging, URLs)
    - services/: Reusable services (audio, mode switching, debugging)
    - workflows/: Automation workflow runners
    - pages/: Page Objects representing different application pages
    - components/: Reusable UI components (modals, dialogs)
    - locators/: Centralized element locators for each page
"""

# Main bot class
from .bot import RosettaStoneBot

# Configuration
from .config import AppConfig, BrowserConfig

# Browser management
from .browser import BrowserManager

# Core module
from .core import (
    Timeouts,
    WaitTimes,
    URLs,
    Logger,
    LogLevel,
    get_logger,
)

# Services
from .services import (
    AudioPlayerService,
    ModeSwitcherService,
    DebugService,
    FrameFinderService,
    TimeTracker,
    get_user_status,
    list_all_users,
)

# Workflows
from .workflows import (
    BaseWorkflow,
    StoriesWorkflow,
    LessonWorkflow,
)

# Page Objects
from .pages import (
    BasePage,
    LoginPage,
    LaunchpadPage,
    StoriesPage,
    LessonPage,
)

# Components
from .components import (
    AudioModal,
    CookieConsent,
    VoiceModal,
)

# Locators
from .locators import (
    LoginLocators,
    StoriesLocators,
    LessonLocators,
    LaunchpadLocators,
    CommonLocators,
)

# Exceptions
from .exceptions import (
    RosettaBotError,
    BrowserError,
    AuthenticationError,
    NavigationError,
    ConfigurationError,
)

__version__ = "3.0.0"

__all__ = [
    # Main bot
    "RosettaStoneBot",
    # Configuration
    "AppConfig",
    "BrowserConfig",
    # Browser
    "BrowserManager",
    # Core
    "Timeouts",
    "WaitTimes",
    "URLs",
    "Logger",
    "LogLevel",
    "get_logger",
    # Services
    "AudioPlayerService",
    "ModeSwitcherService",
    "DebugService",
    "FrameFinderService",
    "TimeTracker",
    "get_user_status",
    "list_all_users",
    # Workflows
    "BaseWorkflow",
    "StoriesWorkflow",
    "LessonWorkflow",
    # Pages
    "BasePage",
    "LoginPage",
    "LaunchpadPage",
    "StoriesPage",
    "LessonPage",
    # Components
    "AudioModal",
    "CookieConsent",
    "VoiceModal",
    # Locators
    "LoginLocators",
    "StoriesLocators",
    "LessonLocators",
    "LaunchpadLocators",
    "CommonLocators",
    # Exceptions
    "RosettaBotError",
    "BrowserError",
    "AuthenticationError",
    "NavigationError",
    "ConfigurationError",
]
