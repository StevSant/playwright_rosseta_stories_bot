"""Audio Modal component for handling audio confirmation dialogs."""

import time

from playwright.sync_api import Page

from ..locators import CommonLocators
from ..core import Timeouts, WaitTimes


class AudioModal:
    """
    Reusable component for handling audio confirmation modals.

    These modals appear when entering stories or lessons, asking
    the user to confirm audio is enabled.
    """

    def __init__(self, page: Page, debug_enabled: bool = False):
        """
        Initialize the Audio Modal component.

        Args:
            page: Playwright Page object
            debug_enabled: Whether to enable debug mode
        """
        self._page = page
        self._debug_enabled = debug_enabled
        self._locators = CommonLocators()

    def dismiss_if_present(self) -> bool:
        """
        Attempt to dismiss audio confirmation modal if present.

        Tries multiple strategies to find and click the continue button.

        Returns:
            True if modal was dismissed, False otherwise
        """
        # Give modal time to appear
        time.sleep(WaitTimes.VERY_SHORT_WAIT)

        # Strategy 1: data-qa="PromptButton" (most specific)
        if self._try_click(self._locators.AUDIO_MODAL_PROMPT_BUTTON, "PromptButton"):
            return True

        # Strategy 2: Button role with "Continuar" text
        try:
            continue_btn = self._page.get_by_role("button", name="Continuar")
            if continue_btn.count() > 0 and continue_btn.first.is_visible():
                self._log("Audio modal detected (button role), clicking 'Continuar'...")
                continue_btn.first.click()
                time.sleep(WaitTimes.SHORT_WAIT)
                self._log("Audio modal dismissed.")
                return True
        except Exception:
            pass

        # Strategy 3: data-qa="continue"
        if self._try_click(self._locators.AUDIO_MODAL_CONTINUE, "data-qa continue"):
            return True

        return False

    def _try_click(self, selector: str, description: str) -> bool:
        """
        Try to click an element by selector.

        Args:
            selector: CSS selector
            description: Description for logging

        Returns:
            True if click successful, False otherwise
        """
        try:
            element = self._page.locator(selector)
            if element.count() > 0 and element.first.is_visible():
                self._log(
                    f"Audio modal detected ({description}), clicking 'Continuar'..."
                )
                element.first.click()
                time.sleep(WaitTimes.SHORT_WAIT)
                self._log("Audio modal dismissed.")
                return True
        except Exception:
            pass
        return False

    def _log(self, message: str, level: str = "DEBUG") -> None:
        """Log a message with level prefix."""
        print(f"[{level}] {message}")
