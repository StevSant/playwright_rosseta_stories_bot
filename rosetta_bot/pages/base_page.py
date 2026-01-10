"""Base Page class implementing common Page Object Model functionality."""

import time
from typing import Optional, Callable
from abc import ABC

from playwright.sync_api import Page, Locator, Frame

from ..core import Timeouts, WaitTimes
from ..services import DebugService


class BasePage(ABC):
    """
    Abstract base class for all Page Objects.

    Provides common functionality for page interactions following
    the Page Object Model pattern.
    """

    def __init__(self, page: Page, debug_enabled: bool = False):
        """
        Initialize the base page.

        Args:
            page: Playwright Page object
            debug_enabled: Whether to enable debug screenshots
        """
        self._page = page
        self._debug_enabled = debug_enabled
        self._debug = DebugService(page, enabled=debug_enabled)

    @property
    def page(self) -> Page:
        """Get the Playwright page object."""
        return self._page

    @property
    def url(self) -> str:
        """Get current page URL."""
        return self._page.url

    @property
    def title(self) -> str:
        """Get current page title."""
        return self._page.title()

    # ==================== Navigation ====================

    def navigate_to(
        self,
        url: str,
        wait_until: str = "networkidle",
        timeout: int = Timeouts.VERY_LONG_TIMEOUT,
    ) -> None:
        """
        Navigate to a URL and wait for load.

        Args:
            url: URL to navigate to
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')
            timeout: Timeout in milliseconds
        """
        self._page.goto(url, wait_until=wait_until, timeout=timeout)

    def reload(self, wait_until: str = "networkidle") -> None:
        """Reload the current page."""
        self._page.reload(wait_until=wait_until)

    def wait_for_load(
        self, state: str = "networkidle", timeout: int = Timeouts.LONG_TIMEOUT
    ) -> None:
        """
        Wait for page to reach a load state.

        Args:
            state: Load state to wait for
            timeout: Timeout in milliseconds
        """
        self._page.wait_for_load_state(state, timeout=timeout)

    # ==================== Element Interactions ====================

    def click_safe(
        self,
        locator: Locator,
        timeout: int = Timeouts.DEFAULT_TIMEOUT,
        scroll: bool = True,
        force: bool = False,
        wait_enabled: bool = False,
    ) -> bool:
        """
        Safely click an element with error handling.

        Args:
            locator: Playwright locator for the element
            timeout: Timeout in milliseconds
            scroll: Whether to scroll element into view first
            force: Whether to force click (bypass actionability checks)
            wait_enabled: Whether to wait for element to be enabled first

        Returns:
            True if click was successful, False otherwise
        """
        try:
            if wait_enabled:
                # Wait for the element to be enabled (not disabled)
                locator.wait_for(state="visible", timeout=timeout)
                self._page.wait_for_function(
                    "el => !el.disabled",
                    arg=locator.element_handle(timeout=timeout),
                    timeout=timeout,
                )
            if scroll:
                locator.scroll_into_view_if_needed()
            locator.click(timeout=timeout, force=force)
            return True
        except Exception as e:
            self._log(f"Click failed: {e}", level="WARN")
            return False

    def fill_safe(
        self, locator: Locator, text: str, timeout: int = Timeouts.DEFAULT_TIMEOUT
    ) -> bool:
        """
        Safely fill a form field with error handling.

        Args:
            locator: Playwright locator for the input
            text: Text to fill
            timeout: Timeout in milliseconds

        Returns:
            True if fill was successful, False otherwise
        """
        try:
            locator.wait_for(state="visible", timeout=timeout)
            locator.fill(text)
            return True
        except Exception as e:
            self._log(f"Fill failed: {e}", level="WARN")
            return False

    def is_visible(
        self, locator: Locator, timeout: int = Timeouts.SHORT_TIMEOUT
    ) -> bool:
        """
        Check if an element is visible.

        Args:
            locator: Playwright locator
            timeout: Timeout in milliseconds

        Returns:
            True if element is visible, False otherwise
        """
        try:
            return locator.is_visible(timeout=timeout)
        except Exception:
            return False

    def wait_for_element(
        self,
        locator: Locator,
        state: str = "visible",
        timeout: int = Timeouts.DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Wait for an element to reach a specific state.

        Args:
            locator: Playwright locator
            state: State to wait for ('visible', 'hidden', 'attached', 'detached')
            timeout: Timeout in milliseconds

        Returns:
            True if element reached state, False on timeout
        """
        try:
            locator.wait_for(state=state, timeout=timeout)
            return True
        except Exception:
            return False

    def get_element_count(self, locator: Locator) -> int:
        """Get the count of matching elements."""
        return locator.count()

    def get_text(
        self, locator: Locator, timeout: int = Timeouts.SHORT_TIMEOUT
    ) -> Optional[str]:
        """
        Get text content of an element.

        Args:
            locator: Playwright locator
            timeout: Timeout in milliseconds

        Returns:
            Element text or None if not found
        """
        try:
            return locator.inner_text(timeout=timeout)
        except Exception:
            return None

    # ==================== Frame Handling ====================

    def find_in_frames(self, selector: str) -> Optional[Locator]:
        """
        Find an element in the main page or any iframe.

        Args:
            selector: CSS selector to find

        Returns:
            Locator if found, None otherwise
        """
        # Try main page first
        try:
            loc = self._page.locator(selector).first
            if loc.is_visible(timeout=Timeouts.SHORT_TIMEOUT):
                return loc
        except Exception:
            pass

        # Try frames
        for frame in self._page.frames:
            try:
                floc = frame.locator(selector).first
                if floc.is_visible(timeout=Timeouts.SHORT_TIMEOUT):
                    return floc
            except Exception:
                continue

        return None

    # ==================== Wait Helpers ====================

    def wait(self, seconds: float) -> None:
        """Wait for specified seconds."""
        time.sleep(seconds)

    def short_wait(self) -> None:
        """Short pause between actions."""
        time.sleep(WaitTimes.SHORT_WAIT)

    def medium_wait(self) -> None:
        """Medium pause for page loads."""
        time.sleep(WaitTimes.MEDIUM_WAIT)

    def very_short_wait(self) -> None:
        """Very short pause for UI updates."""
        time.sleep(WaitTimes.VERY_SHORT_WAIT)

    # ==================== Debug Helpers ====================

    def take_screenshot(self, name: str) -> None:
        """Take a debug screenshot if debugging is enabled."""
        self._debug.dump(name)

    def _log(self, message: str, level: str = "INFO") -> None:
        """Log a message with level prefix."""
        print(f"[{level}] {message}")

    # ==================== Dialog Handling ====================

    def setup_dialog_auto_dismiss(self) -> None:
        """Configure dialogs to be automatically dismissed."""
        self._page.on("dialog", lambda dialog: dialog.dismiss())

    # ==================== Retry Logic ====================

    def retry_action(
        self, action: Callable[[], bool], max_retries: int = 3, delay: float = 1.0
    ) -> bool:
        """
        Retry an action with exponential backoff.

        Args:
            action: Callable that returns True on success
            max_retries: Maximum number of retries
            delay: Initial delay between retries in seconds

        Returns:
            True if action succeeded, False after all retries failed
        """
        for attempt in range(max_retries):
            try:
                if action():
                    return True
            except Exception as e:
                self._log(f"Attempt {attempt + 1} failed: {e}", level="WARN")

            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))

        return False
