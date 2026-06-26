"""Configuration for the fast Stories usage-reporting capability."""

import os
from dataclasses import dataclass

from ..core import app_base_dir
from ..exceptions import ConfigurationError

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

# Default state directory: <project root>/state/
_DEFAULT_STATE_DIR = str(app_base_dir() / "state")

# Sentinel "no throttle" value (in hours). When the session window and daily
# cap are this large, a single run credits the entire remaining target at once.
# Far above any realistic TARGET_HOURS, so the only binding limit is the
# remaining cumulative goal. Override the caps via env to re-enable throttling.
_NO_CAP_HOURS = 100_000.0


@dataclass
class FastReportConfig:
    """
    Configuration for ``FastStoriesRunner``.

    The fast path opens N parallel browser contexts, establishes a valid LCP
    session per context, then credits Stories hours directly via the
    ``app_usage`` API instead of playing stories in real time.

    Accumulation settings
    ~~~~~~~~~~~~~~~~~~~~~~
    By default the bot is **uncapped**: a single run credits the entire
    remaining TARGET_HOURS at once.  Set the env vars below to re-enable
    gradual, human-like accumulation across scheduled runs.

    SESSION_HOURS_MIN / SESSION_HOURS_MAX
        Each invocation credits a random amount of hours in this range.
        Defaults are effectively unlimited (``_NO_CAP_HOURS``) so one run
        finishes the goal.  Set both (e.g. 0.5 / 2.0) to spread TARGET_HOURS
        over many runs like a real learner.

    MAX_HOURS_PER_DAY
        Hard daily cap: once this many hours are credited for the calendar
        day, subsequent runs exit immediately without touching the browser.
        Defaults to unlimited; set it (e.g. 2.5) to throttle per day.

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
    # Accumulation caps. Default: uncapped — one run completes the full target.
    session_hours_min: float = _NO_CAP_HOURS
    session_hours_max: float = _NO_CAP_HOURS
    max_hours_per_day: float = _NO_CAP_HOURS
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
            session_hours_min=float(os.getenv("SESSION_HOURS_MIN", str(_NO_CAP_HOURS))),
            session_hours_max=float(os.getenv("SESSION_HOURS_MAX", str(_NO_CAP_HOURS))),
            max_hours_per_day=float(os.getenv("MAX_HOURS_PER_DAY", str(_NO_CAP_HOURS))),
            state_dir=os.getenv("STATE_DIR", _DEFAULT_STATE_DIR),
            state_key=os.getenv("STATE_KEY", ""),
        )
