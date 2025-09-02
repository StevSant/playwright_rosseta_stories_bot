"""Main bot class for Rosetta Stone automation."""

from typing import Optional

from playwright.sync_api import Playwright, Page

from .config import AppConfig
from .browser import BrowserManager
from .authentication import AuthenticationService
from .navigation import LessonNavigator
from .activities import LessonActivityManager
from .stories_feature_manager import StoriesFeatureManager


class RosettaStoneBot:
    """Main bot orchestrator that coordinates all services."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.browser_manager = BrowserManager(config.browser)
        self.auth_service = AuthenticationService(config.email, config.password)
        self.page: Optional[Page] = None
        self.navigator: Optional[LessonNavigator] = None
        self.activity_manager: Optional[LessonActivityManager] = None
        self.stories_manager: Optional[StoriesFeatureManager] = None

    def run(self, playwright: Playwright) -> None:
        """Run the complete bot workflow."""
        try:
            self._launch_browser(playwright)
            self._login()
            self._navigate_to_lesson()
            self._start_activity_loop()
        finally:
            self._cleanup()

    def _launch_browser(self, playwright: Playwright) -> None:
        """Launch browser and initialize page."""
        print("[INFO] Browser started.")
        self.page = self.browser_manager.launch(playwright)

        # Initialize other services that depend on the page
        self.navigator = LessonNavigator(self.page)
        self.activity_manager = LessonActivityManager(
            self.page, self.config.debug_enabled
        )
        self.stories_manager = StoriesFeatureManager(
            self.page, self.config.debug_enabled
        )

    def _login(self) -> None:
        """Perform user authentication."""
        if not self.page:
            raise RuntimeError("Browser not launched")
        self.auth_service.login(self.page)

    def _navigate_to_lesson(self) -> None:
        """Navigate to the target lesson."""
        if not self.navigator:
            raise RuntimeError("Navigator not initialized")
        self.navigator.navigate_to_lesson()

    def _start_activity_loop(self) -> None:
        """Start the lesson activity loop."""
        if not self.activity_manager:
            raise RuntimeError("Activity manager not initialized")
        self.activity_manager.start_activity_loop()

    def run_stories_checklist(self, playwright: Playwright) -> None:
        """Run the bot with stories checklist workflow."""
        try:
            self._launch_browser(playwright)
            self._login()
            self._run_stories_feature()
        finally:
            self._cleanup()

    def run_stories_checklist_only(self) -> None:
        """Run only the stories checklist feature (assumes browser and login are ready)."""
        if not self.stories_manager:
            raise RuntimeError("Stories manager not initialized")
        self.stories_manager.checklist_on_histories()

    def run_infinite_stories_loop(self, playwright: Playwright) -> None:
        """Run the bot with infinite stories loop workflow."""
        try:
            self._launch_browser(playwright)
            self._login()
            self._run_infinite_stories_feature()
        finally:
            self._cleanup()

    def _run_infinite_stories_feature(self) -> None:
        """Execute the infinite stories loop feature."""
        if not self.stories_manager:
            raise RuntimeError("Stories manager not initialized")
        self.stories_manager.loop_all_histories()

    def _run_stories_feature(self) -> None:
        """Execute the stories checklist feature."""
        if not self.stories_manager:
            raise RuntimeError("Stories manager not initialized")
        self.stories_manager.checklist_on_histories()

    def _cleanup(self) -> None:
        """Clean up resources."""
        self.browser_manager.close()
        print("[INFO] Bot finished, script terminated.")
