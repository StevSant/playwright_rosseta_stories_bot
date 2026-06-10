"""
Rosetta Stone - Orchestrator entry point.

Strategy: fast first, browser bot as fallback.

  1. Run `fast_stories_v3` — N parallel sessions that credit Stories hours
     directly via the `app_usage` API. This is fast and is the approach that
     actually moves the institution admin dashboard.

  2. If v3 makes no progress (no session established, or the API stops
     crediting hours because it got blocked/changed), fall back to the full
     Playwright bot in `rosetta_bot`, which plays Stories the slow, legit way
     through a real browser.

Usage:
  uv run python run.py              # uses .env
  uv run python run.py .env_daniela # specific env file (same convention as v3)

Importing `fast_stories_v3` triggers its `load_dotenv(sys.argv[1])`, so the
fallback bot's `AppConfig.from_env()` reads the very same variables — no
duplicate config loading here.

Environment variables (in addition to those read by fast_stories_v3 / the bot):
  FALLBACK_MIN_HOURS  - if v3 credits fewer hours than this, fall back to the
                        full browser bot (default: 0.1)
  FALLBACK_MODE       - which bot workflow to run as fallback:
                        "stories" (default) or "lesson"
"""

import asyncio
import os

from playwright.sync_api import sync_playwright

# NOTE: importing this module loads the env file (its module-level
# load_dotenv runs on import), which must happen before AppConfig.from_env().
import fast_stories_v3
from rosetta_bot import AppConfig, RosettaStoneBot

FALLBACK_MIN_HOURS = float(os.environ.get("FALLBACK_MIN_HOURS", "0.1"))
FALLBACK_MODE = os.environ.get("FALLBACK_MODE", "stories").strip().lower()


def needs_fallback(result: dict) -> bool:
    """Decide whether v3 made no meaningful progress."""
    if not result:
        return True
    if result.get("active_sessions", 0) == 0:
        return True
    if result.get("hours_reported", 0.0) < FALLBACK_MIN_HOURS:
        return True
    return False


def run_fallback_bot() -> None:
    """Run the full Playwright bot the slow, legit way."""
    config = AppConfig.from_env()

    with sync_playwright() as playwright:
        bot = RosettaStoneBot(config)

        if FALLBACK_MODE == "lesson":
            print("[INFO] Fallback: running infinite lesson loop...")
            bot.run_infinite_lesson_loop(playwright)
        else:
            print("[INFO] Fallback: running infinite stories loop...")
            bot.run_infinite_stories_loop(playwright)


def main() -> None:
    print("=" * 60)
    print("Rosetta Stone Orchestrator - fast_stories_v3 first, bot fallback")
    print("=" * 60)

    # Phase 1: fast API reporting. Its asyncio loop fully exits here before
    # we ever open sync_playwright below (sync Playwright cannot run nested
    # inside a running asyncio loop).
    result = asyncio.run(fast_stories_v3.main())

    print(
        f"[INFO] fast_stories_v3 result: "
        f"active_sessions={result.get('active_sessions')} "
        f"hours_reported={result.get('hours_reported', 0.0):.2f} "
        f"failed_sessions={result.get('failed_sessions')}"
    )

    # Phase 2: fallback only if v3 made no progress.
    if needs_fallback(result):
        print(
            f"[WARN] v3 credited < {FALLBACK_MIN_HOURS}h or established no "
            f"session. Falling back to the full Playwright bot."
        )
        run_fallback_bot()
    else:
        print("[INFO] v3 credited hours successfully. No fallback needed.")


if __name__ == "__main__":
    main()
