"""Voice Modal component for handling voice recognition dialogs."""

import time

from playwright.sync_api import Page

from ..locators import CommonLocators
from ..core import Timeouts, WaitTimes


class VoiceModal:
    """
    Reusable component for handling "Continue without voice" modals.

    These modals appear when entering lessons asking if the user
    wants to continue without voice recognition.
    """

    def __init__(self, page: Page, debug_enabled: bool = False):
        """
        Initialize the Voice Modal component.

        Args:
            page: Playwright Page object
            debug_enabled: Whether to enable debug mode
        """
        self._page = page
        self._debug_enabled = debug_enabled
        self._locators = CommonLocators()

    def dismiss_if_present(
        self, wait_for_visible: bool = False, timeout: int = Timeouts.SHORT_TIMEOUT
    ) -> bool:
        """
        Attempt to dismiss "Continue without voice" modal if present.

        Args:
            wait_for_visible: Whether to wait for modal to become visible
            timeout: Timeout in milliseconds

        Returns:
            True if modal was dismissed, False otherwise
        """
        try:
            continue_btn = self._page.get_by_role("button").filter(
                has_text=self._locators.CONTINUE_WITHOUT_VOICE_PATTERN
            )

            if wait_for_visible:
                continue_btn.first.wait_for(state="visible", timeout=timeout)

            if continue_btn.count() > 0:
                continue_btn.first.click()
                self._log("'Continue without voice' button clicked.")
                time.sleep(WaitTimes.VERY_SHORT_WAIT)
                return True

        except Exception:
            self._log("'Continue without voice' modal not present or already handled.")

        return False

    def wait_and_dismiss(self, timeout: int = Timeouts.VERY_LONG_TIMEOUT) -> bool:
        """
        Wait for voice modal and dismiss it.

        Used during lesson entry when the modal is expected to appear.

        Args:
            timeout: Timeout in milliseconds to wait for modal

        Returns:
            True if modal was found and dismissed, False otherwise
        """
        return self.dismiss_if_present(wait_for_visible=True, timeout=timeout)

    def _log(self, message: str, level: str = "DEBUG") -> None:
        """Log a message with level prefix."""
        print(f"[{level}] {message}")
