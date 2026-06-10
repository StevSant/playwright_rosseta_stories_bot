"""
Orchestrator - fast first, full browser bot as fallback.

Strategy:
  1. Run the fast path (``FastStoriesRunner``) which credits Stories hours
     directly via the ``app_usage`` API across N parallel sessions.
  2. If the fast path makes no progress (no session established, or hours
     credited below ``FALLBACK_MIN_HOURS`` because the API got blocked or
     changed), fall back to the full Playwright bot, which plays Stories the
     slow, legit way through a real browser.

The async fast phase runs to completion (its event loop fully exits) before
the sync ``sync_playwright`` phase opens - sync Playwright cannot run nested
inside a running asyncio loop.
"""

import asyncio
import os
from typing import Optional

from playwright.sync_api import sync_playwright

from .bot import RosettaStoneBot
from .config import AppConfig
from .core import Logger, get_logger
from .fast import FastReportConfig, FastReportResult, FastStoriesRunner


class Orchestrator:
    """Coordinates the fast path and the browser-bot fallback."""

    def __init__(
        self,
        fallback_min_hours: float = 0.1,
        fallback_mode: str = "stories",
        logger: Optional[Logger] = None,
    ):
        self._fallback_min_hours = fallback_min_hours
        self._fallback_mode = fallback_mode.strip().lower()
        self._logger = logger or get_logger("Orchestrator")

    @classmethod
    def from_env(cls) -> "Orchestrator":
        """Create an orchestrator from environment variables."""
        return cls(
            fallback_min_hours=float(os.getenv("FALLBACK_MIN_HOURS", "0.1")),
            fallback_mode=os.getenv("FALLBACK_MODE", "stories"),
        )

    def run(self) -> None:
        """Run the fast path, then the fallback bot if needed."""
        self._logger.info("Orchestrator: fast path first, browser bot as fallback.")

        # Phase 1: fast API reporting. Its asyncio loop fully exits here before
        # we ever open sync_playwright below.
        result = asyncio.run(FastStoriesRunner(FastReportConfig.from_env()).run())
        self._logger.info(
            f"Fast path result: active_sessions={result.active_sessions} "
            f"hours_reported={result.hours_reported:.2f} "
            f"failed_sessions={result.failed_sessions}"
        )

        # Phase 2: fallback only if the fast path made no progress.
        if self._needs_fallback(result):
            self._logger.warn(
                f"Fast path credited < {self._fallback_min_hours}h or established "
                f"no session. Falling back to the full browser bot."
            )
            self._run_fallback_bot()
        else:
            self._logger.info("Fast path credited hours successfully. No fallback needed.")

    def _needs_fallback(self, result: FastReportResult) -> bool:
        if result.active_sessions == 0:
            return True
        if result.hours_reported < self._fallback_min_hours:
            return True
        return False

    def _run_fallback_bot(self) -> None:
        config = AppConfig.from_env()
        with sync_playwright() as playwright:
            bot = RosettaStoneBot(config)
            if self._fallback_mode == "lesson":
                self._logger.info("Fallback: running infinite lesson loop...")
                bot.run_infinite_lesson_loop(playwright)
            else:
                self._logger.info("Fallback: running infinite stories loop...")
                bot.run_infinite_stories_loop(playwright)
