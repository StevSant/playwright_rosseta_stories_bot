"""Configuration for the fast Stories usage-reporting capability."""

import os
from dataclasses import dataclass

from ..exceptions import ConfigurationError

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


@dataclass
class FastReportConfig:
    """
    Configuration for ``FastStoriesRunner``.

    The fast path opens N parallel browser contexts, establishes a valid LCP
    session per context, then credits Stories hours directly via the
    ``app_usage`` API instead of playing stories in real time.
    """

    email: str
    password: str
    target_hours: float = 35.0
    parallel_sessions: int = 5
    chunk_min_sec: int = 300
    chunk_max_sec: int = 900
    report_delay_sec: float = 0.5
    headless: bool = True
    language: str = "ENG"
    user_agent: str = _DEFAULT_USER_AGENT

    @classmethod
    def from_env(cls) -> "FastReportConfig":
        """Create configuration from environment variables."""
        email = os.getenv("ROSETTA_EMAIL")
        password = os.getenv("ROSETTA_PASSWORD")

        if not email or not password:
            raise ConfigurationError(
                "ROSETTA_EMAIL and ROSETTA_PASSWORD environment variables are required"
            )

        headless = os.getenv("BROWSER_HEADLESS", "1").lower() not in ("0", "false", "no")

        return cls(
            email=email,
            password=password,
            target_hours=float(os.getenv("TARGET_HOURS", "35")),
            parallel_sessions=int(os.getenv("PARALLEL_SESSIONS", "5")),
            chunk_min_sec=int(os.getenv("REPORT_CHUNK_MIN_SEC", "300")),
            chunk_max_sec=int(os.getenv("REPORT_CHUNK_MAX_SEC", "900")),
            report_delay_sec=float(os.getenv("REPORT_DELAY_SEC", "0.5")),
            headless=headless,
            language=os.getenv("STORIES_LANGUAGE", "ENG"),
        )
