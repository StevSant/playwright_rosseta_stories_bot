"""Lesson workflow for repeating a specific lesson."""

from playwright.sync_api import Page

from .base_workflow import BaseWorkflow
from ..core import Logger, get_logger
from ..components import VoiceModal
from ..locators import LessonLocators


class LessonWorkflow(BaseWorkflow):
    """
    Workflow for repeating a lesson in an infinite loop.

    Responsibilities:
    - Run activity cycles (play, rewind, pause, toggle)
    - Detect lesson completion
    - Restart lesson when completed
    """

    def __init__(self, page: Page, debug_enabled: bool = False, logger: Logger = None):
        """
        Initialize the lesson workflow.

        Args:
            page: Playwright Page object
            debug_enabled: Whether debugging is enabled
            logger: Optional logger instance
        """
        super().__init__(page, debug_enabled, logger or get_logger("LessonWorkflow"))

        # Locators
        self._locators = LessonLocators()

        # Components
        self._voice_modal = VoiceModal(page, debug_enabled)

    def setup(self) -> bool:
        """
        Setup the lesson workflow.

        Assumes navigation to lesson is already done.

        Returns:
            True (lesson is already loaded)
        """
        self._logger.info("Lesson workflow ready.")
        self._take_debug_screenshot("lesson_workflow_start")
        return True

    def run_once(self) -> bool:
        """
        Run one complete lesson cycle.

        Executes activity cycles until lesson is completed,
        then restarts the lesson.

        Returns:
            True if cycle completed successfully
        """
        # Run activity cycles
        cycles_completed = self._run_lesson_cycles()

        # Check and handle completion
        if self._is_lesson_completed():
            self._logger.info("Lesson completed, restarting...")
            self._restart_lesson()

        return cycles_completed > 0

    def _run_lesson_cycles(self, max_cycles: int = 10) -> int:
        """
        Run multiple activity cycles.

        Args:
            max_cycles: Maximum cycles before checking completion

        Returns:
            Number of cycles completed
        """
        for cycle in range(max_cycles):
            self._logger.loop(f"Cycle {cycle + 1}/{max_cycles}")

            self._run_activity_cycle()

            if self._is_lesson_completed():
                return cycle + 1

            self._logger.loop("Cycle completed.")

        return max_cycles

    def _is_lesson_completed(self) -> bool:
        """
        Check if the lesson has been completed.

        Returns:
            True if completion indicators found
        """
        try:
            indicators = [
                self._page.get_by_text(self._locators.COMPLETION_PATTERN),
                self._page.get_by_text(self._locators.NEXT_LESSON_PATTERN),
                self._page.get_by_role("button", name=self._locators.CONTINUE_PATTERN),
            ]

            for indicator in indicators:
                if indicator.count() > 0 and indicator.first.is_visible():
                    self._logger.debug("Lesson completion detected.")
                    return True

            return False
        except Exception:
            return False

    def _restart_lesson(self) -> bool:
        """
        Restart the current lesson.

        Returns:
            True if restart successful
        """
        try:
            self._logger.info("Restarting lesson...")

            # Try restart button
            restart_btn = self._page.get_by_role(
                "button", name=self._locators.RESTART_PATTERN
            )

            if restart_btn.count() > 0:
                restart_btn.first.click()
                self._logger.debug("Restart button clicked.")
                self._wait(3)
                return True

            # Fallback: reload page
            self._logger.debug("Using page reload to restart.")
            self._page.reload(wait_until="networkidle")
            self._wait(3)

            # Handle modals
            self._voice_modal.dismiss_if_present()
            self._mode.set_listen_mode()

            return True

        except Exception as e:
            self._logger.error(f"Restart failed: {e}")
            return False

    def run_standard_loop(self) -> None:
        """
        Run standard activity loop (non-infinite, until interrupted).

        This is the legacy behavior for basic lesson activity.
        """
        self._logger.info("Starting standard activity loop...")
        self._take_debug_screenshot("activity_loop_start")

        cycle = 0

        try:
            while True:
                cycle += 1
                self._logger.loop(f"Iteration {cycle}")

                self._run_activity_cycle()

                self._logger.loop("Cycle completed, repeating...")

        except KeyboardInterrupt:
            self._logger.info("Activity loop interrupted by user.")
