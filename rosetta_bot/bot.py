"""
Rosetta Stone Bot - Main Orchestrator

This module provides the main bot class that orchestrates all automation
workflows using a clean, modular architecture.

Responsibilities:
- Browser lifecycle management
- Authentication
- Workflow delegation
"""

from typing import Optional

from playwright.sync_api import Playwright, Page

from .config import AppConfig
from .browser import BrowserManager
from .core import get_logger
from .pages import LoginPage, LaunchpadPage
from .workflows import StoriesWorkflow, LessonWorkflow


class RosettaStoneBot:
    """
    Main bot orchestrator.

    Coordinates browser lifecycle, authentication, and workflow execution.
    Each workflow handles its own specific logic independently.
    """

    def __init__(self, config: AppConfig):
        """
        Initialize the bot.

        Args:
            config: Application configuration
        """
        self._config = config
        self._browser_manager = BrowserManager(config.browser)
        self._logger = get_logger("Bot")
        self._page: Optional[Page] = None

    @property
    def page(self) -> Page:
        """Get the current page."""
        if not self._page:
            raise RuntimeError("Browser not launched")
        return self._page

    # ==================== Public Workflow Methods ====================

    def run(self, playwright: Playwright) -> None:
        """
        Run standard lesson workflow (single run with activity loop).

        Args:
            playwright: Playwright instance
        """
        self._execute_workflow(
            playwright,
            workflow_name="StandardLesson",
            navigate_to_lesson=True,
            run_method=self._run_standard_lesson,
        )

    def run_infinite_stories_loop(self, playwright: Playwright) -> None:
        """
        Run infinite stories loop workflow.

        Args:
            playwright: Playwright instance
        """
        self._execute_workflow(
            playwright,
            workflow_name="InfiniteStories",
            navigate_to_lesson=False,
            run_method=self._run_stories_workflow,
        )

    def run_infinite_lesson_loop(self, playwright: Playwright) -> None:
        """
        Run infinite lesson loop workflow.

        Args:
            playwright: Playwright instance
        """
        self._execute_workflow(
            playwright,
            workflow_name="InfiniteLesson",
            navigate_to_lesson=True,
            run_method=self._run_lesson_workflow,
        )

    def run_stories_checklist(self, playwright: Playwright) -> None:
        """
        Run the stories checklist workflow (legacy compatibility).

        Args:
            playwright: Playwright instance
        """
        self.run_infinite_stories_loop(playwright)

    # ==================== Workflow Execution ====================

    def _execute_workflow(
        self,
        playwright: Playwright,
        workflow_name: str,
        navigate_to_lesson: bool,
        run_method,
    ) -> None:
        """
        Execute a workflow with common setup and teardown.

        Args:
            playwright: Playwright instance
            workflow_name: Name for logging
            navigate_to_lesson: Whether to navigate to lesson first
            run_method: Method to execute the specific workflow
        """
        try:
            self._logger.info(f"Starting {workflow_name} workflow...")

            self._initialize(playwright)
            self._authenticate()

            if navigate_to_lesson:
                self._navigate_to_lesson()

            run_method()

        finally:
            self._cleanup()

    def _run_stories_workflow(self) -> None:
        """Execute the stories workflow."""
        workflow = StoriesWorkflow(
            self._page,
            debug_enabled=self._config.debug_enabled,
            logger=get_logger("Stories"),
        )
        workflow.run_infinite()

    def _run_lesson_workflow(self) -> None:
        """Execute the infinite lesson workflow."""
        workflow = LessonWorkflow(
            self._page,
            debug_enabled=self._config.debug_enabled,
            logger=get_logger("Lesson"),
        )
        workflow.run_infinite()

    def _run_standard_lesson(self) -> None:
        """Execute the standard lesson activity loop."""
        workflow = LessonWorkflow(
            self._page,
            debug_enabled=self._config.debug_enabled,
            logger=get_logger("Lesson"),
        )
        workflow.run_standard_loop()

    # ==================== Setup Methods ====================

    def _initialize(self, playwright: Playwright) -> None:
        """Initialize browser."""
        self._logger.info("Initializing browser...")
        self._page = self._browser_manager.launch(playwright)
        self._logger.info("Browser initialized.")

    def _authenticate(self) -> None:
        """Perform authentication."""
        login_page = LoginPage(self._page, self._config.debug_enabled)

        success = login_page.login(self._config.email, self._config.password)

        if not success:
            raise RuntimeError("Authentication failed")

    def _navigate_to_lesson(self) -> None:
        """Navigate to the target lesson."""
        launchpad = LaunchpadPage(
            self._page,
            self._config.debug_enabled,
            lesson_name=self._config.lesson_name,
        )
        launchpad.navigate_to_lesson()

    def _cleanup(self) -> None:
        """Clean up resources."""
        self._browser_manager.close()
        self._logger.info("Bot finished.")
