"""Launchpad Page Object for navigation and course selection."""

import time

from playwright.sync_api import Page

from .base_page import BasePage
from ..locators import LaunchpadLocators
from ..core import WaitTimes


class LaunchpadPage(BasePage):
    """
    Page Object for the Rosetta Stone Launchpad.

    Handles navigation from launchpad to different sections:
    - Foundations
    - Stories
    - Specific lessons
    """

    def __init__(
        self,
        page: Page,
        debug_enabled: bool = False,
        lesson_name: str = "A Visit to Hollywood|Una visita a Hollywood",
    ):
        """
        Initialize the Launchpad Page.

        Args:
            page: Playwright Page object
            debug_enabled: Whether to enable debug screenshots
            lesson_name: Regex pattern for the target lesson name
        """
        super().__init__(page, debug_enabled)
        self._locators = LaunchpadLocators()
        self._lesson_name = lesson_name

    # ==================== Navigation Actions ====================

    def enter_foundations(self) -> "LaunchpadPage":
        """
        Enter the Foundations/Fundamentos section.

        Returns:
            Self for method chaining
        """
        self._log("Entering 'Foundations/Fundamentos'...")

        foundations_element = self._page.get_by_text(self._locators.FOUNDATIONS_PATTERN)
        self.click_safe(foundations_element)
        self.take_screenshot("foundations")

        return self

    def browse_all_content(self) -> "LaunchpadPage":
        """
        Click on 'Browse all content' / 'Explorar todo el contenido'.

        Returns:
            Self for method chaining
        """
        self._log("Exploring all content...")

        browse_element = self._page.get_by_text(self._locators.BROWSE_CONTENT_PATTERN)
        self.click_safe(browse_element)
        self.take_screenshot("browse_all_content")

        return self

    def select_second_lesson(self) -> "LaunchpadPage":
        """
        Select the second lesson in the list.

        Returns:
            Self for method chaining
        """
        self._log("Selecting second lesson...")

        lesson_link = self._page.locator("a").nth(1)
        self.click_safe(lesson_link)
        self.take_screenshot("selected_second_lesson")

        return self

    def view_all_stories(self) -> "LaunchpadPage":
        """
        Navigate to view all stories from the stories section.

        Returns:
            Self for method chaining
        """
        self._log("Selecting 'View All Stories'...")

        stories_section = self._page.locator(self._locators.STORIES_SECTION)
        see_all_link = stories_section.locator(self._locators.SEE_ALL_LINK)
        self.click_safe(see_all_link)
        self.take_screenshot("view_all_stories")

        return self

    def select_specific_lesson(self) -> "LaunchpadPage":
        """
        Select the specific lesson by name.

        Returns:
            Self for method chaining
        """
        self._log(f"Selecting lesson: {self._lesson_name}")

        import re

        pattern = re.compile(self._lesson_name, re.IGNORECASE)

        book_cover = self._page.locator(
            self._locators.BOOK_COVER_PREFIX,
            has_text=pattern,
        )
        self.click_safe(book_cover)
        self.take_screenshot("entered_specific_lesson")

        return self

    def enter_first_item(self) -> "LaunchpadPage":
        """
        Enter the first item in the launchpad (used for establishing session).

        Returns:
            Self for method chaining
        """
        self._log("Entering first launchpad item...")

        try:
            with self._page.expect_navigation(
                wait_until="domcontentloaded", timeout=30000
            ):
                self._page.get_by_role("listitem").first.click()

            self.medium_wait()
            self._log(f"Navigation complete. URL: {self.url}")

        except Exception as e:
            self._log(f"Navigation from launchpad: {e}", level="DEBUG")

        return self

    # ==================== State Checks ====================

    def is_on_launchpad(self) -> bool:
        """
        Check if currently on the launchpad page.

        Returns:
            True if on launchpad, False otherwise
        """
        return "launchpad" in self.url.lower() or "login.rosettastone.com" in self.url

    # ==================== Full Navigation Flows ====================

    def navigate_to_lesson(self) -> None:
        """Execute the complete navigation flow to a specific lesson."""
        from ..components import VoiceModal

        self.enter_foundations()
        self.browse_all_content()
        self.view_all_stories()
        self.select_specific_lesson()

        # Handle voice modal
        voice_modal = VoiceModal(self._page, self._debug_enabled)
        voice_modal.wait_and_dismiss()
        self.take_screenshot("continue_without_voice")

        # Select listen mode
        self._select_listen_mode()

        # Setup dialog handling
        self.setup_dialog_auto_dismiss()

    def _select_listen_mode(self) -> None:
        """Select the Listen/Escuchar mode."""
        from ..locators import CommonLocators

        self._log("Selecting 'Listen/Escuchar' mode...")

        common = CommonLocators()
        listen_element = self._page.get_by_text(common.LISTEN_PATTERN)
        self.click_safe(listen_element)
        self.take_screenshot("listen_mode")
