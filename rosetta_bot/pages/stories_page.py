"""Stories Page Object for managing stories automation."""

from typing import List, Tuple

from playwright.sync_api import Page, Locator

from .base_page import BasePage
from .launchpad_page import LaunchpadPage
from ..locators import StoriesLocators, CommonLocators
from ..components import AudioModal, VoiceModal
from ..core import WaitTimes, Timeouts


class StoriesPage(BasePage):
    """
    Page Object for the Rosetta Stone Stories page.

    Handles all stories-related interactions including:
    - Navigation to stories section
    - Story discovery and selection
    - Story playback (listen/read cycles)
    - Infinite loop functionality
    """

    def __init__(self, page: Page, debug_enabled: bool = False):
        """
        Initialize the Stories Page.

        Args:
            page: Playwright Page object
            debug_enabled: Whether to enable debug screenshots
        """
        super().__init__(page, debug_enabled)
        self._locators = StoriesLocators()
        self._common_locators = CommonLocators()
        self._audio_modal = AudioModal(page, debug_enabled)
        self._voice_modal = VoiceModal(page, debug_enabled)

    # ==================== Navigation ====================

    def open(self) -> "StoriesPage":
        """
        Navigate directly to the stories page.

        Returns:
            Self for method chaining
        """
        self._log("Navigating directly to stories page...")
        self.navigate_to(
            self._locators.STORIES_URL,
            wait_until="domcontentloaded",
            timeout=Timeouts.VERY_LONG_TIMEOUT,
        )
        self.wait_for_load(timeout=30000)
        self.medium_wait()

        self._log(f"Current URL: {self.url}")
        self._log(f"Page title: {self.title}")

        return self

    def navigate_from_launchpad(self) -> bool:
        """
        Navigate to stories section, handling launchpad if necessary.

        Returns:
            True if navigation successful, False otherwise
        """
        self._log("Navigating to Stories section...")

        # Check if we're on launchpad
        if self._is_on_launchpad():
            self._log("Detected launchpad, entering Foundations first...")
            launchpad = LaunchpadPage(self._page, self._debug_enabled)
            launchpad.enter_first_item()

        # Navigate to stories
        self.open()

        # Handle audio modal if present
        self._audio_modal.dismiss_if_present()

        # Verify we're on the stories page
        if "/stories" not in self.url:
            self._log("Failed to navigate to stories page.", level="WARN")
            self.take_screenshot("stories_page_debug")
            return False

        self._log("Navigation to Stories successful.")
        return self._verify_stories_loaded()

    def _is_on_launchpad(self) -> bool:
        """Check if currently on launchpad."""
        return "launchpad" in self.url or "login.rosettastone.com" in self.url

    def _verify_stories_loaded(self) -> bool:
        """Verify that stories are loaded on the page."""
        stories = self._page.locator(self._locators.STORY_LINKS)
        count = stories.count()

        if count > 0:
            self._log(f"Found {count} stories available.")
            return True

        # Wait and retry
        self._log("Waiting for stories to load...")
        self.short_wait()
        count = stories.count()
        self._log(f"After waiting: {count} stories found.")

        return True

    # ==================== Story Discovery ====================

    def get_available_stories(self) -> List[Tuple[str, Locator]]:
        """
        Find all available stories on the page.

        Returns:
            List of tuples (story_name, locator)
        """
        self.wait_for_load()
        self.medium_wait()

        # Handle audio modal
        self._audio_modal.dismiss_if_present()

        stories_found = []

        self._log(f"Searching for {len(self._locators.KNOWN_STORIES)} known stories...")

        for story_name in self._locators.KNOWN_STORIES:
            try:
                element = self._page.get_by_text(story_name, exact=True)
                if element.count() > 0:
                    self._log(f"✓ Found: {story_name}", level="DEBUG")
                    stories_found.append((story_name, element.first))
                else:
                    self._log(f"✗ Not visible: {story_name}", level="DEBUG")
            except Exception as e:
                self._log(f"Error searching for '{story_name}': {e}", level="DEBUG")

        self._log(f"Found {len(stories_found)} stories to process.")

        if not stories_found:
            self._debug_no_stories_found()

        return stories_found

    def _debug_no_stories_found(self) -> None:
        """Debug helper when no stories are found."""
        self._log("No stories found.", level="WARN")
        self._page.screenshot(path="debug/no_stories_found.png")
        self._log("Screenshot saved to debug/no_stories_found.png", level="DEBUG")

        try:
            page_text = self._page.inner_text("body")
            self._log(f"First 500 chars: {page_text[:500]}", level="DEBUG")
        except Exception:
            pass

    # ==================== Story Processing ====================

    def process_story(self, story_name: str, story_element: Locator) -> bool:
        """
        Process a single story with listen/read cycle.

        Args:
            story_name: Name of the story
            story_element: Locator for the story element

        Returns:
            True if processed successfully, False otherwise
        """
        try:
            self._log(f"Processing story: {story_name}")

            # Click on story
            story_element.scroll_into_view_if_needed()
            self.very_short_wait()
            story_element.click()
            self._log(f"Clicked on '{story_name}' successfully.", level="DEBUG")
            self.short_wait()

            # Execute listen/read cycle
            self._execute_listen_read_cycle(story_name)

            # Return to stories list
            self._return_to_stories_list()

            return True

        except Exception as e:
            self._log(f"Error processing story '{story_name}': {e}", level="ERROR")
            self._return_to_stories_list()
            return False

    def _execute_listen_read_cycle(self, story_title: str) -> None:
        """
        Execute the listen/read cycle for a story.

        Args:
            story_title: Title of the story for logging
        """
        self._log(f"Starting listen/read cycle for '{story_title}'...")

        # Handle modals
        self._audio_modal.dismiss_if_present()
        self._voice_modal.dismiss_if_present()

        # Set initial listen mode
        self._set_listen_mode()

        # Execute cycles
        max_cycles = 5

        for cycle in range(max_cycles):
            self._log(f"Cycle {cycle + 1} in story '{story_title}'", level="DEBUG")

            # Play audio
            self._play_audio()

            # Wait for audio
            self.wait(WaitTimes.ACTIVITY_CYCLE)

            # Alternate modes
            self._alternate_read_listen()

            # Check if story completed
            if self._is_story_completed():
                self._log(f"Story '{story_title}' completed.")
                break

            self.very_short_wait()

    def _set_listen_mode(self) -> None:
        """Set the initial listen mode."""
        try:
            listen_btn = self._page.get_by_text(self._common_locators.LISTEN_PATTERN)
            listen_btn.first.click(timeout=Timeouts.SHORT_TIMEOUT)
            self._log("Listen mode activated.", level="DEBUG")
            self.very_short_wait()
        except Exception:
            self._log(
                "Could not activate listen mode or already active.", level="DEBUG"
            )

    def _play_audio(self) -> None:
        """Play the story audio."""
        try:
            play_btn = self._page.locator(self._locators.PLAY_BUTTON).nth(
                self._locators.PLAY_BUTTON_INDEX
            )
            play_btn.click(timeout=Timeouts.SHORT_TIMEOUT)
            self._log("Audio started (polygon).", level="DEBUG")
        except Exception:
            try:
                circle_btn = self._page.locator(self._locators.CIRCLE_BUTTON)
                circle_btn.click(timeout=Timeouts.SHORT_TIMEOUT)
                self._log("Audio started (circle).", level="DEBUG")
            except Exception:
                self._log("Could not start audio with known methods.", level="DEBUG")

    def _alternate_read_listen(self) -> None:
        """Alternate between read and listen modes."""
        try:
            # Switch to read mode
            read_btn = self._page.get_by_text(self._common_locators.READ_PATTERN)
            read_btn.first.click(timeout=Timeouts.SHORT_TIMEOUT)
            self._log("Switched to read mode.", level="DEBUG")
            self.very_short_wait()

            # Switch back to listen mode
            listen_btn = self._page.get_by_text(self._common_locators.LISTEN_PATTERN)
            listen_btn.first.click(timeout=Timeouts.SHORT_TIMEOUT)
            self._log("Switched to listen mode.", level="DEBUG")
            self.very_short_wait()

        except Exception as e:
            self._log(f"Error alternating read/listen modes: {e}", level="DEBUG")

    def _is_story_completed(self) -> bool:
        """Check if the current story is completed."""
        try:
            # Check completion indicator
            completion = self._page.get_by_text(self._locators.COMPLETION_PATTERN)
            if completion.count() > 0:
                return True

            # Check next story button
            next_story = self._page.get_by_text(self._locators.NEXT_STORY_PATTERN)
            if next_story.count() > 0:
                return True

            return False
        except Exception:
            return False

    def _return_to_stories_list(self) -> bool:
        """Return to the stories list."""
        try:
            self.navigate_to(self._locators.STORIES_URL, wait_until="networkidle")
            self._log("Returned to stories list.", level="DEBUG")
            self.short_wait()
            return True
        except Exception as e:
            self._log(f"Failed to return to stories list: {e}", level="ERROR")
            return False

    # ==================== Infinite Loop ====================

    def run_infinite_loop(self) -> None:
        """
        Run infinite loop through all stories.

        Processes all stories repeatedly until interrupted.
        """
        self._log("Starting infinite stories loop...")

        # Initial navigation
        if not self.navigate_from_launchpad():
            self._log("Could not access Stories section.", level="ERROR")
            return

        iteration = 0

        try:
            while True:
                iteration += 1
                self._log(f"=== Complete iteration #{iteration} ===")

                self._process_all_stories_once()

                self._log(f"Iteration #{iteration} completed. Restarting cycle...")
                self.short_wait()

        except KeyboardInterrupt:
            self._log("Infinite loop interrupted by user.")
        except Exception as e:
            self._log(f"Error in infinite loop: {e}", level="ERROR")

    def _process_all_stories_once(self) -> None:
        """Process all available stories once."""
        self._log("Processing all available stories...")

        stories = self.get_available_stories()
        total = len(stories)

        if total == 0:
            self._log("No stories found to process.", level="WARN")
            return

        for i, (story_name, story_element) in enumerate(stories):
            self._log(f"=== Story {i + 1}/{total}: {story_name} ===")

            self.process_story(story_name, story_element)

            self.very_short_wait()

    # ==================== Legacy Compatibility ====================

    def checklist_on_histories(self) -> None:
        """Legacy method for backwards compatibility."""
        self._log("checklist_on_histories() has been refactored.")
        self._log("Redirecting to run_infinite_loop()...")
        self.run_infinite_loop()
