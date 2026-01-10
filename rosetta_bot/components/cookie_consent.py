"""Cookie Consent component for handling cookie banners."""

from playwright.sync_api import Page

from ..locators import CommonLocators
from ..core import Timeouts


class CookieConsent:
    """
    Reusable component for handling cookie consent banners.

    Can be used across different pages where cookie banners may appear.
    """

    def __init__(self, page: Page, debug_enabled: bool = False):
        """
        Initialize the Cookie Consent component.

        Args:
            page: Playwright Page object
            debug_enabled: Whether to enable debug mode
        """
        self._page = page
        self._debug_enabled = debug_enabled
        self._locators = CommonLocators()

    def dismiss_if_present(self) -> bool:
        """
        Attempt to dismiss cookie consent banner if present.

        Returns:
            True if banner was dismissed, False otherwise
        """
        # Strategy 1: Click accept button by text pattern
        try:
            accept_btn = self._page.get_by_role("button").filter(
                has_text=self._locators.COOKIE_ACCEPT_PATTERN
            )
            accept_btn.first.click(timeout=Timeouts.SHORT_TIMEOUT)
            self._log("Cookie banner accepted.")
            return True
        except Exception:
            pass

        # Strategy 2: Click close button
        try:
            close_btn = self._page.locator(self._locators.COOKIE_CLOSE_BUTTON).first
            close_btn.click(timeout=Timeouts.COOKIE_TIMEOUT)
            self._log("Cookie banner closed.")
            return True
        except Exception:
            pass

        return False

    def _log(self, message: str, level: str = "INFO") -> None:
        """Log a message with level prefix."""
        print(f"[{level}] {message}")
