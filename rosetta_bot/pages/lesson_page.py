"""Lesson Page Object for managing lesson activity automation."""

from playwright.sync_api import Page

from .base_page import BasePage
from ..locators import LessonLocators, CommonLocators
from ..components import VoiceModal
from ..core import WaitTimes


class LessonPage(BasePage):
    """
    Page Object for the Rosetta Stone Lesson page.

    Handles all lesson-related interactions including:
    - Audio playback control
    - Mode switching (listen/read)
    - Lesson completion detection
    - Infinite loop functionality
    """

    def __init__(self, page: Page, debug_enabled: bool = False):
        """
        Initialize the Lesson Page.

        Args:
            page: Playwright Page object
            debug_enabled: Whether to enable debug screenshots
        """
        super().__init__(page, debug_enabled)
        self._locators = LessonLocators()
        self._common_locators = CommonLocators()
        self._voice_modal = VoiceModal(page, debug_enabled)

    # ==================== Audio Controls ====================

    def play_audio(self) -> bool:
        """
        Start audio playback.

        Returns:
            True if successful, False otherwise
        """
        try:
            play_btn = self._page.locator(self._locators.PLAY_CONTROL).nth(
                self._locators.PLAY_CONTROL_INDEX
            )
            play_btn.click()
            return True
        except Exception:
            self._log("Play control not found.", level="WARN")
            return False

    def pause_audio(self) -> bool:
        """
        Pause audio playback.

        Returns:
            True if successful, False otherwise
        """
        self._log("Pausing audio...", level="LOOP")
        try:
            pause_btn = self._page.locator(self._locators.PAUSE_CONTROL).nth(
                self._locators.PAUSE_CONTROL_INDEX
            )
            pause_btn.click()
            self.wait(5)
            return True
        except Exception:
            return False

    def rewind_audio(self) -> bool:
        """
        Rewind audio by 10 seconds.

        Returns:
            True if successful, False otherwise
        """
        self._log("Rewinding 10 seconds...", level="LOOP")
        try:
            self._page.get_by_text(self._locators.REWIND_TEXT).click()
            self.wait(5)
            return True
        except Exception:
            return False

    # ==================== Mode Controls ====================

    def set_listen_mode(self) -> bool:
        """
        Switch to listen mode.

        Returns:
            True if successful, False otherwise
        """
        try:
            listen_btn = self._page.get_by_text(self._common_locators.LISTEN_PATTERN)
            if listen_btn.count() > 0:
                listen_btn.first.click()
                self._log("Listen mode selected.", level="DEBUG")
                self.wait(1)
                return True
        except Exception:
            pass
        return False

    def set_read_mode(self) -> bool:
        """
        Switch to read mode.

        Returns:
            True if successful, False otherwise
        """
        try:
            read_btn = self._page.get_by_text(self._common_locators.READ_PATTERN)
            if read_btn.count() > 0:
                read_btn.first.click()
                self._log("Read mode selected.", level="DEBUG")
                self.wait(1)
                return True
        except Exception:
            pass
        return False

    def toggle_modes(self) -> None:
        """Toggle between read and listen modes."""
        self._log("Secondary actions: Read and Listen...", level="LOOP")
        try:
            self.set_read_mode()
            self.wait(5)
            self.set_listen_mode()
        except Exception:
            pass
        self.wait(5)

    # ==================== Lesson State ====================

    def is_lesson_completed(self) -> bool:
        """
        Check if the lesson has been completed.

        Returns:
            True if lesson is completed, False otherwise
        """
        try:
            completion_indicators = [
                self._page.get_by_text(self._locators.COMPLETION_PATTERN),
                self._page.get_by_text(self._locators.NEXT_LESSON_PATTERN),
                self._page.get_by_role("button", name=self._locators.CONTINUE_PATTERN),
            ]

            for indicator in completion_indicators:
                if indicator.count() > 0 and indicator.first.is_visible():
                    self._log("Lesson completion indicator found.", level="DEBUG")
                    return True

            return False
        except Exception:
            return False

    def restart_lesson(self) -> bool:
        """
        Restart the current lesson.

        Returns:
            True if restart successful, False otherwise
        """
        try:
            self._log("Restarting lesson...")

            # Try restart button first
            restart_btn = self._page.get_by_role(
                "button", name=self._locators.RESTART_PATTERN
            )
            if restart_btn.count() > 0:
                restart_btn.first.click()
                self._log("Restart button clicked.", level="DEBUG")
                self.wait(3)
                return True

            # Fallback: reload page
            current_url = self.url
            self._log(f"Reloading URL: {current_url}", level="DEBUG")
            self.reload()
            self.wait(3)

            # Handle modals after reload
            self._voice_modal.dismiss_if_present()
            self.set_listen_mode()

            return True

        except Exception as e:
            self._log(f"Error restarting lesson: {e}", level="ERROR")
            return False

    # ==================== Activity Cycle ====================

    def run_activity_cycle(self) -> None:
        """Execute a single activity cycle (play, wait, rewind, pause, toggle)."""
        self.play_audio()
        self._wait_and_debug(WaitTimes.ACTIVITY_CYCLE)
        self.rewind_audio()
        self.pause_audio()
        self.toggle_modes()

    def _wait_and_debug(self, seconds: float, iteration: int = 0) -> None:
        """
        Wait and optionally take debug screenshot.

        Args:
            seconds: Seconds to wait
            iteration: Current iteration number for naming screenshots
        """
        self.wait(seconds)

        if self._debug_enabled and iteration <= 3:
            try:
                self.take_screenshot(f"activity_iter_{iteration}")
            except Exception:
                pass

    # ==================== Infinite Loop ====================

    def run_infinite_loop(self) -> None:
        """
        Run infinite lesson loop.

        Continuously repeats the lesson activity cycle until interrupted.
        """
        self._log("Starting infinite lesson loop...")

        if self._debug_enabled:
            self.take_screenshot("before_infinite_lesson_loop")

        lesson_iteration = 0

        try:
            while True:
                lesson_iteration += 1
                self._log(f"=== Lesson iteration #{lesson_iteration} ===")

                # Run lesson cycle
                self._run_single_lesson_cycle()

                # Check completion and restart if needed
                if self.is_lesson_completed():
                    self._log("Lesson completed, restarting...")
                    self.restart_lesson()
                else:
                    self._log("Continuing with lesson...")

                self._log(f"Iteration #{lesson_iteration} completed.")
                self.wait(2)

        except KeyboardInterrupt:
            self._log("Infinite lesson loop interrupted by user.")

    def _run_single_lesson_cycle(self) -> None:
        """Execute a single lesson cycle with multiple activity cycles."""
        max_cycles = 10

        for cycle in range(max_cycles):
            self._log(f"Cycle {cycle + 1}: Playing audio...", level="LOOP")

            self.run_activity_cycle()

            if self.is_lesson_completed():
                break

            self._log("Cycle completed.", level="LOOP")

    def run_standard_activity_loop(self) -> None:
        """
        Run standard activity loop (non-infinite).

        Continuously cycles through activities until interrupted.
        """
        self._log("Starting activity loop to keep lesson active...")

        if self._debug_enabled:
            self.take_screenshot("before_activity_loop")

        iteration = 0

        try:
            while True:
                iteration += 1
                self._log(f"Iteration {iteration}: Playing audio...", level="LOOP")

                self.run_activity_cycle()

                self._log("Cycle completed, repeating...", level="LOOP")

        except KeyboardInterrupt:
            self._log("Loop interrupted by user.")
