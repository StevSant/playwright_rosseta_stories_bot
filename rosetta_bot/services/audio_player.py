"""Audio player service for controlling media playback."""

from playwright.sync_api import Page

from ..core import Logger, Timeouts, WaitTimes, get_logger


class AudioPlayerService:
    """
    Service for controlling audio playback in lessons and stories.

    Handles play, pause, and rewind operations with fallback strategies.

    Responsibility: Audio playback control ONLY
    """

    # Default selectors for audio controls
    PLAY_BUTTON = "polygon"
    PLAY_BUTTON_INDEX = 3
    CIRCLE_BUTTON = "circle"
    PAUSE_BUTTON = "rect"
    PAUSE_BUTTON_INDEX = 1
    REWIND_TEXT = "10"

    def __init__(self, page: Page, logger: Logger = None):
        """
        Initialize the audio player service.

        Args:
            page: Playwright Page object
            logger: Optional logger instance
        """
        self._page = page
        self._logger = logger or get_logger("AudioPlayer")

    def play(self) -> bool:
        """
        Start audio playback.

        Tries multiple strategies to find and click the play button.

        Returns:
            True if playback started, False otherwise
        """
        # Strategy 1: Polygon button
        if self._try_click_polygon():
            return True

        # Strategy 2: Circle button
        if self._try_click_circle():
            return True

        self._logger.warn("Could not start audio with known methods.")
        return False

    def _try_click_polygon(self) -> bool:
        """Try to click the polygon play button."""
        try:
            play_btn = self._page.locator(self.PLAY_BUTTON).nth(self.PLAY_BUTTON_INDEX)
            play_btn.click(timeout=Timeouts.SHORT)
            self._logger.debug("Audio started (polygon).")
            return True
        except Exception:
            return False

    def _try_click_circle(self) -> bool:
        """Try to click the circle play button."""
        try:
            circle_btn = self._page.locator(self.CIRCLE_BUTTON)
            circle_btn.click(timeout=Timeouts.SHORT)
            self._logger.debug("Audio started (circle).")
            return True
        except Exception:
            return False

    def pause(self) -> bool:
        """
        Pause audio playback.

        Returns:
            True if paused successfully, False otherwise
        """
        try:
            pause_btn = self._page.locator(self.PAUSE_BUTTON).nth(
                self.PAUSE_BUTTON_INDEX
            )
            pause_btn.click()
            self._logger.debug("Audio paused.")
            return True
        except Exception:
            self._logger.warn("Could not pause audio.")
            return False

    def rewind(self, seconds: int = 10) -> bool:
        """
        Rewind audio by specified seconds.

        Args:
            seconds: Number of seconds to rewind (default: 10)

        Returns:
            True if rewound successfully, False otherwise
        """
        try:
            self._page.get_by_text(str(seconds)).click()
            self._logger.debug(f"Audio rewound by {seconds} seconds.")
            return True
        except Exception:
            self._logger.warn(f"Could not rewind audio by {seconds}s.")
            return False
