"""Base workflow class with common functionality."""

import time
from abc import ABC, abstractmethod
from typing import Optional

from playwright.sync_api import Page

from ..core import Logger, WaitTimes, get_logger
from ..services import AudioPlayerService, ModeSwitcherService, DebugService


class BaseWorkflow(ABC):
    """
    Abstract base class for all workflows.

    Provides common functionality for workflow execution including:
    - Audio playback control
    - Mode switching
    - Debug utilities
    - Iteration management

    Subclasses must implement the specific workflow logic.
    """

    def __init__(self, page: Page, debug_enabled: bool = False, logger: Logger = None):
        """
        Initialize the base workflow.

        Args:
            page: Playwright Page object
            debug_enabled: Whether debugging is enabled
            logger: Optional logger instance
        """
        self._page = page
        self._debug_enabled = debug_enabled
        self._logger = logger or get_logger(self.__class__.__name__)

        # Initialize services
        self._audio = AudioPlayerService(page, self._logger)
        self._mode = ModeSwitcherService(page, self._logger)
        self._debug = DebugService(page, enabled=debug_enabled, logger=self._logger)

        # Workflow state
        self._iteration = 0
        self._running = False

    @abstractmethod
    def run_once(self) -> bool:
        """
        Run the workflow once.

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def setup(self) -> bool:
        """
        Setup the workflow before running.

        Returns:
            True if setup successful, False otherwise
        """
        pass

    def run_infinite(self) -> None:
        """
        Run the workflow in an infinite loop.

        Continues until interrupted by user (Ctrl+C).
        """
        self._logger.info(f"Starting infinite {self.__class__.__name__}...")

        if not self.setup():
            self._logger.error("Workflow setup failed.")
            return

        self._running = True

        try:
            while self._running:
                self._iteration += 1
                self._logger.info(f"=== Iteration #{self._iteration} ===")

                success = self.run_once()

                if success:
                    self._logger.info(f"Iteration #{self._iteration} completed.")
                else:
                    self._logger.warn(f"Iteration #{self._iteration} had errors.")

                self._wait(WaitTimes.SHORT)

        except KeyboardInterrupt:
            self._logger.info("Workflow interrupted by user.")
        except Exception as e:
            self._logger.error(f"Workflow error: {e}")
        finally:
            self._running = False

    def stop(self) -> None:
        """Stop the workflow gracefully."""
        self._running = False

    # ==================== Helper Methods ====================

    def _wait(self, seconds: float) -> None:
        """Wait for specified seconds."""
        time.sleep(seconds)

    def _run_activity_cycle(self) -> None:
        """
        Run a single activity cycle.

        Plays audio, waits, rewinds, pauses, and toggles modes.
        """
        self._logger.loop("Playing audio...")
        self._audio.play()

        self._wait(WaitTimes.ACTIVITY_CYCLE)

        self._logger.loop("Rewinding...")
        self._audio.rewind()
        self._wait(5)

        self._logger.loop("Pausing...")
        self._audio.pause()
        self._wait(5)

        self._logger.loop("Toggling modes...")
        self._mode.alternate_modes(wait_seconds=5)
        self._wait(5)

    def _take_debug_screenshot(self, tag: str) -> None:
        """Take a debug screenshot if enabled."""
        if self._debug_enabled:
            self._debug.dump(tag)
