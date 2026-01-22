"""Launchpad Page Object for navigation and course selection."""

import os
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

    # Valor por defecto para el nombre de la lección
    DEFAULT_LESSON_NAME = "A Visit to Hollywood|Una visita a Hollywood"

    # Lecciones de fallback en caso de que la principal no se encuentre
    FALLBACK_LESSONS = [
        "Driving",
        "Cats",
        "At the Airport",
        "A Man Is Walking",
        "The Big Yellow Sun",
    ]

    def __init__(
        self,
        page: Page,
        debug_enabled: bool = False,
        lesson_name: str | None = None,
    ):
        """
        Initialize the Launchpad Page.

        Args:
            page: Playwright Page object
            debug_enabled: Whether to enable debug screenshots
            lesson_name: Regex pattern for the target lesson name.
                         If None, reads from LESSON_NAME env var or uses default.
        """
        super().__init__(page, debug_enabled)
        self._locators = LaunchpadLocators()
        # Prioridad: parámetro > variable de entorno > valor por defecto
        self._lesson_name = lesson_name or os.getenv(
            "LESSON_NAME", self.DEFAULT_LESSON_NAME
        )

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
        Select the specific lesson by name, with fallback to alternative lessons.

        Tries the configured lesson first, then falls back to FALLBACK_LESSONS
        if not found.

        Returns:
            Self for method chaining
        """
        import re

        # Lista de lecciones a intentar: primero la configurada, luego los fallbacks
        lessons_to_try = [self._lesson_name] + self.FALLBACK_LESSONS

        for lesson_name in lessons_to_try:
            self._log(f"Searching for lesson: {lesson_name}")

            pattern = re.compile(lesson_name, re.IGNORECASE)

            book_cover = self._page.locator(
                self._locators.BOOK_COVER_PREFIX,
                has_text=pattern,
            )

            # Verificar si el elemento existe y es visible
            try:
                if book_cover.count() > 0 and book_cover.first.is_visible(timeout=2000):
                    self._log(f"Found lesson: {lesson_name}")
                    self.click_safe(book_cover.first)
                    self.take_screenshot("entered_specific_lesson")
                    return self
            except Exception:
                self._log(f"Lesson '{lesson_name}' not found, trying next...")
                continue

        # Si ninguna lección fue encontrada, intentar con la primera disponible
        self._log("No specific lesson found, selecting first available story...")
        first_book = self._page.locator(self._locators.BOOK_COVER_PREFIX).first
        self.click_safe(first_book)
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
