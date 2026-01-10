"""Mode switcher service for Listen/Read mode transitions."""

import re
from typing import Pattern

from playwright.sync_api import Page

from ..core import Logger, Timeouts, get_logger


class ModeSwitcherService:
    """
    Service for switching between Listen and Read modes.

    Handles mode detection and switching with fallback strategies.

    Responsibility: Mode switching ONLY
    """

    # Compiled patterns for mode buttons
    LISTEN_PATTERN: Pattern[str] = re.compile(r"escuchar|listen", re.IGNORECASE)
    READ_PATTERN: Pattern[str] = re.compile(r"leer|read", re.IGNORECASE)

    def __init__(self, page: Page, logger: Logger = None):
        """
        Initialize the mode switcher service.

        Args:
            page: Playwright Page object
            logger: Optional logger instance
        """
        self._page = page
        self._logger = logger or get_logger("ModeSwitcher")

    def set_listen_mode(self) -> bool:
        """
        Switch to Listen mode.

        Returns:
            True if switch successful, False otherwise
        """
        return self._set_mode(self.LISTEN_PATTERN, "Listen")

    def set_read_mode(self) -> bool:
        """
        Switch to Read mode.

        Returns:
            True if switch successful, False otherwise
        """
        return self._set_mode(self.READ_PATTERN, "Read")

    def _set_mode(self, pattern: Pattern[str], mode_name: str) -> bool:
        """
        Set a specific mode.

        Args:
            pattern: Regex pattern for the mode button
            mode_name: Name for logging

        Returns:
            True if successful, False otherwise
        """
        try:
            button = self._page.get_by_text(pattern)
            if button.count() > 0:
                button.first.click(timeout=Timeouts.SHORT)
                self._logger.debug(f"{mode_name} mode activated.")
                return True
            self._logger.debug(f"{mode_name} mode button not found.")
            return False
        except Exception as e:
            self._logger.debug(f"Could not set {mode_name} mode: {e}")
            return False

    def alternate_modes(self, wait_seconds: float = 2.0) -> None:
        """
        Alternate between Read and Listen modes.

        Args:
            wait_seconds: Seconds to wait between switches
        """
        import time

        self._logger.debug("Alternating modes: Read -> Listen")

        if self.set_read_mode():
            time.sleep(wait_seconds)

        self.set_listen_mode()

    def toggle(self) -> None:
        """Toggle between current and alternate mode."""
        self.alternate_modes()
