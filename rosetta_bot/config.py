"""Configuration management for the Rosetta Stone Bot."""

import os
from dataclasses import dataclass

from .exceptions import ConfigurationError


@dataclass
class BrowserConfig:
    """Configuration for browser settings."""

    headless: bool = True
    slow_mo: int = 500
    viewport_width: int = 1366
    viewport_height: int = 768
    locale: str = "es-ES"
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    )


@dataclass
class AppConfig:
    """Main application configuration."""

    email: str
    password: str
    browser: BrowserConfig
    debug_enabled: bool = True
    lesson_name: str = "A Visit to Hollywood|Una visita a Hollywood"
    target_hours: float = 35.0

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables."""
        email = os.getenv("EMAIL")
        password = os.getenv("PASSWORD")

        if not email or not password:
            raise ConfigurationError(
                "EMAIL and PASSWORD environment variables are required"
            )

        headless_env = os.getenv("PLAYWRIGHT_HEADLESS", "1")
        headless = headless_env.lower() not in ("0", "false", "no")

        slow_mo = int(os.getenv("PLAYWRIGHT_SLOW_MO", "500"))
        debug_enabled = os.getenv("DEBUG", "1").lower() not in ("0", "false", "no")

        browser_config = BrowserConfig(headless=headless, slow_mo=slow_mo)

        lesson_name = os.getenv(
            "LESSON_NAME", "A Visit to Hollywood|Una visita a Hollywood"
        )

        target_hours = float(os.getenv("TARGET_HOURS", "35.0"))

        return cls(
            email=email,
            password=password,
            browser=browser_config,
            debug_enabled=debug_enabled,
            lesson_name=lesson_name,
            target_hours=target_hours,
        )
