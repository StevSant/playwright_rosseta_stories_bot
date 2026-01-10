"""Stories workflow for processing all stories in a loop."""

from typing import List, Tuple

from playwright.sync_api import Page, Locator

from .base_workflow import BaseWorkflow
from ..core import Logger, WaitTimes, Timeouts, URLs, get_logger
from ..components import AudioModal, VoiceModal
from ..locators import StoriesLocators, CommonLocators


class StoriesWorkflow(BaseWorkflow):
    """
    Workflow for processing stories in an infinite loop.

    Responsibilities:
    - Navigate to stories section
    - Discover available stories
    - Process each story with listen/read cycles
    - Loop through all stories repeatedly
    """

    def __init__(self, page: Page, debug_enabled: bool = False, logger: Logger = None):
        """
        Initialize the stories workflow.

        Args:
            page: Playwright Page object
            debug_enabled: Whether debugging is enabled
            logger: Optional logger instance
        """
        super().__init__(page, debug_enabled, logger or get_logger("StoriesWorkflow"))

        # Locators
        self._locators = StoriesLocators()
        self._common_locators = CommonLocators()

        # Components
        self._audio_modal = AudioModal(page, debug_enabled)
        self._voice_modal = VoiceModal(page, debug_enabled)

    def setup(self) -> bool:
        """
        Navigate to stories section.

        Returns:
            True if navigation successful, False otherwise
        """
        self._logger.info("Setting up stories workflow...")

        # Handle launchpad if needed
        if self._is_on_launchpad():
            self._logger.info("Detected launchpad, entering Foundations...")
            self._enter_foundations()

        # Navigate to stories
        return self._navigate_to_stories()

    def run_once(self) -> bool:
        """
        Process all stories once.

        Returns:
            True if all stories processed, False otherwise
        """
        stories = self._discover_stories()

        if not stories:
            self._logger.warn("No stories found.")
            return False

        success_count = 0
        total = len(stories)

        for i, (name, element) in enumerate(stories):
            self._logger.info(f"=== Story {i + 1}/{total}: {name} ===")

            if self._process_story(name, element):
                success_count += 1

            self._wait(WaitTimes.VERY_SHORT)

        self._logger.info(f"Processed {success_count}/{total} stories.")
        return success_count > 0

    # ==================== Navigation ====================

    def _is_on_launchpad(self) -> bool:
        """Check if on launchpad page."""
        url = self._page.url.lower()
        return "launchpad" in url or "login.rosettastone.com" in url

    def _enter_foundations(self) -> None:
        """Enter Foundations from launchpad."""
        try:
            self._page.get_by_role("listitem").first.click()
            self._wait(WaitTimes.MEDIUM)
        except Exception as e:
            self._logger.warn(f"Could not enter Foundations: {e}")

    def _navigate_to_stories(self) -> bool:
        """Navigate to stories page."""
        self._logger.info("Navigating to stories...")

        try:
            self._page.goto(
                URLs.STORIES, wait_until="domcontentloaded", timeout=Timeouts.VERY_LONG
            )
            self._page.wait_for_load_state("networkidle", timeout=30000)
            self._wait(WaitTimes.MEDIUM)

            # Handle audio modal
            self._audio_modal.dismiss_if_present()

            # Verify navigation
            if "/stories" not in self._page.url:
                self._logger.warn(f"Not on stories page: {self._page.url}")
                return False

            self._logger.info("Navigation to stories successful.")
            return True

        except Exception as e:
            self._logger.error(f"Navigation failed: {e}")
            return False

    # ==================== Story Discovery ====================

    def _discover_stories(self) -> List[Tuple[str, Locator]]:
        """
        Find all available stories.

        Returns:
            List of (story_name, locator) tuples
        """
        self._page.wait_for_load_state("networkidle")
        self._wait(WaitTimes.MEDIUM)

        self._audio_modal.dismiss_if_present()

        stories = []

        for name in self._locators.KNOWN_STORIES:
            try:
                element = self._page.get_by_text(name, exact=True)
                if element.count() > 0:
                    self._logger.debug(f"✓ Found: {name}")
                    stories.append((name, element.first))
            except Exception:
                pass

        self._logger.info(f"Discovered {len(stories)} stories.")
        return stories

    # ==================== Story Processing ====================

    def _process_story(self, name: str, element: Locator) -> bool:
        """
        Process a single story.

        Args:
            name: Story name
            element: Story element locator

        Returns:
            True if processed successfully, False otherwise
        """
        try:
            # Click on story
            element.scroll_into_view_if_needed()
            self._wait(WaitTimes.VERY_SHORT)
            element.click()
            self._logger.debug(f"Entered story: {name}")
            self._wait(WaitTimes.SHORT)

            # Handle modals
            self._audio_modal.dismiss_if_present()
            self._voice_modal.dismiss_if_present()

            # Set listen mode
            self._mode.set_listen_mode()

            # Run activity cycles
            self._run_story_cycles(name)

            # Return to stories list
            self._return_to_stories()

            return True

        except Exception as e:
            self._logger.error(f"Error processing '{name}': {e}")
            self._return_to_stories()
            return False

    def _run_story_cycles(self, name: str, max_cycles: int = 5) -> None:
        """
        Run listen/read cycles for a story.

        Args:
            name: Story name for logging
            max_cycles: Maximum number of cycles
        """
        for cycle in range(max_cycles):
            self._logger.debug(f"Cycle {cycle + 1} for '{name}'")

            self._audio.play()
            self._wait(WaitTimes.ACTIVITY_CYCLE)
            self._mode.alternate_modes()

            if self._is_story_completed():
                self._logger.info(f"Story '{name}' completed.")
                break

            self._wait(WaitTimes.VERY_SHORT)

    def _is_story_completed(self) -> bool:
        """Check if story is completed."""
        try:
            completion = self._page.get_by_text(self._locators.COMPLETION_PATTERN)
            if completion.count() > 0:
                return True

            next_btn = self._page.get_by_text(self._locators.NEXT_STORY_PATTERN)
            if next_btn.count() > 0:
                return True

            return False
        except Exception:
            return False

    def _return_to_stories(self) -> None:
        """Return to stories list."""
        try:
            self._page.goto(URLs.STORIES, wait_until="networkidle")
            self._wait(WaitTimes.SHORT)
        except Exception as e:
            self._logger.warn(f"Could not return to stories: {e}")
