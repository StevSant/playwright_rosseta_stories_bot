"""Frame finder service for locating elements across iframes."""

from typing import Optional, Tuple, Union

from playwright.sync_api import Page, Frame, Locator

from ..core import Logger, Timeouts, get_logger


class FrameFinderService:
    """
    Service for finding elements across frames and iframes.

    Handles the complexity of searching through nested frames.

    Responsibility: Frame traversal and element location ONLY
    """

    def __init__(self, page: Page, logger: Logger = None):
        """
        Initialize the frame finder service.

        Args:
            page: Playwright Page object
            logger: Optional logger instance
        """
        self._page = page
        self._logger = logger or get_logger("FrameFinder")

    def find_in_any_frame(
        self, selector: str, timeout: int = Timeouts.SHORT
    ) -> Tuple[Optional[Union[Frame, Page]], Optional[Locator]]:
        """
        Find an element in the main page or any iframe.

        Args:
            selector: CSS selector to search for
            timeout: Timeout for visibility check

        Returns:
            Tuple of (frame_or_page, locator) or (None, None) if not found
        """
        # Try main page first
        result = self._try_find_in_context(self._page, selector, timeout)
        if result[1] is not None:
            return result

        # Try all frames
        for frame in self._page.frames:
            result = self._try_find_in_context(frame, selector, timeout // 2)
            if result[1] is not None:
                return result

        return None, None

    def _try_find_in_context(
        self, context: Union[Page, Frame], selector: str, timeout: int
    ) -> Tuple[Optional[Union[Frame, Page]], Optional[Locator]]:
        """
        Try to find an element in a specific context.

        Args:
            context: Page or Frame to search in
            selector: CSS selector
            timeout: Timeout in milliseconds

        Returns:
            Tuple of (context, locator) or (None, None)
        """
        try:
            locator = context.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            return context, locator
        except Exception:
            return None, None

    def find_visible(
        self, selector: str, timeout: int = Timeouts.SHORT
    ) -> Optional[Locator]:
        """
        Find a visible element, returning just the locator.

        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds

        Returns:
            Locator if found and visible, None otherwise
        """
        _, locator = self.find_in_any_frame(selector, timeout)
        return locator

    def exists_in_any_frame(self, selector: str) -> bool:
        """
        Check if an element exists in any frame.

        Args:
            selector: CSS selector

        Returns:
            True if element exists, False otherwise
        """
        return self.find_visible(selector, timeout=Timeouts.VERY_SHORT) is not None
