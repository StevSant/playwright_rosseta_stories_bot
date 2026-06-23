"""Configuration for the fast Stories usage-reporting capability."""

import os
from dataclasses import dataclass

from ..core import app_base_dir
from ..exceptions import ConfigurationError

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

# Default state directory: <project root>/state/ from source, or
# <exe dir>/state/ when frozen. Never resolved from __file__, which under a
# PyInstaller one-file build points into the wiped-on-exit _MEI temp dir.
_DEFAULT_STATE_DIR = str(app_base_dir() / "state")


@dataclass
class FastReportConfig:
    """
    Configuration for ``FastStoriesRunner``.

    The fast path opens N parallel browser contexts, establishes a valid LCP
    session per context, then credits Stories hours directly via the
    ``app_usage`` API instead of playing stories in real time.

    Speed mode
    ~~~~~~~~~~
    HUMAN_MODE
        When false (the default) the runner is *fast*: it credits the full
        remaining TARGET_HOURS in a single run, ignoring the per-run session
        window and the daily cap, with no jittered delay between POSTs.
        Set HUMAN_MODE=1 to restore the gradual, human-like accumulation
        described below (session window + daily cap + jittered POST delays).

    Gradual-accumulation settings (only applied when HUMAN_MODE is on)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SESSION_HOURS_MIN / SESSION_HOURS_MAX
        Each invocation credits a random amount of hours in this range.
        Running once or twice a day via Task Scheduler spreads TARGET_HOURS
        over many weeks like a real learner.

    MAX_HOURS_PER_DAY
        Hard daily cap: once this many hours are credited for the calendar
        day, subsequent runs exit immediately without touching the browser.

    STATE_DIR
        Directory where per-account JSON progress files are stored.

    STATE_KEY
        Override the account identifier used as the state file stem.
        Defaults to the account email address.

    Report-pacing settings
    ~~~~~~~~~~~~~~~~~~~~~~
    REPORT_DELAY_MIN_SEC / REPORT_DELAY_MAX_SEC
        Each POST is followed by a jittered sleep in this range (seconds),
        replacing the old fixed REPORT_DELAY_SEC.
    """

    email: str
    password: str
    target_hours: float = 35.0
    # Fast by default: credit the full target in one run. Flip to True (via
    # HUMAN_MODE) for gradual, human-like accumulation across many runs.
    human_mode: bool = False
    parallel_sessions: int = 2
    chunk_min_sec: int = 300
    chunk_max_sec: int = 900
    # Jittered inter-POST delay (replaces old fixed report_delay_sec).
    report_delay_min_sec: float = 1.5
    report_delay_max_sec: float = 6.0
    headless: bool = True
    language: str = "ENG"
    user_agent: str = _DEFAULT_USER_AGENT
    # Gradual-accumulation caps.
    session_hours_min: float = 0.5
    session_hours_max: float = 2.0
    max_hours_per_day: float = 2.5
    # State persistence.
    state_dir: str = _DEFAULT_STATE_DIR
    state_key: str = ""  # Defaults to email when empty.

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
        human_mode = os.getenv("HUMAN_MODE", "0").lower() in ("1", "true", "yes")

        return cls(
            email=email,
            password=password,
            target_hours=float(os.getenv("TARGET_HOURS", "35")),
            human_mode=human_mode,
            parallel_sessions=int(os.getenv("PARALLEL_SESSIONS", "2")),
            chunk_min_sec=int(os.getenv("REPORT_CHUNK_MIN_SEC", "300")),
            chunk_max_sec=int(os.getenv("REPORT_CHUNK_MAX_SEC", "900")),
            report_delay_min_sec=float(os.getenv("REPORT_DELAY_MIN_SEC", "1.5")),
            report_delay_max_sec=float(os.getenv("REPORT_DELAY_MAX_SEC", "6.0")),
            headless=headless,
            language=os.getenv("STORIES_LANGUAGE", "ENG"),
            session_hours_min=float(os.getenv("SESSION_HOURS_MIN", "0.5")),
            session_hours_max=float(os.getenv("SESSION_HOURS_MAX", "2.0")),
            max_hours_per_day=float(os.getenv("MAX_HOURS_PER_DAY", "2.5")),
            state_dir=os.getenv("STATE_DIR", _DEFAULT_STATE_DIR),
            state_key=os.getenv("STATE_KEY", ""),
        )
