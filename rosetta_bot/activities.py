"""Activity management for Rosetta Stone lessons."""

import time
import re

from playwright.sync_api import Page

from . import utils


class LessonActivityManager:
    """Manages lesson activities to keep the lesson active."""

    def __init__(self, page: Page, debug_enabled: bool = True):
        self.page = page
        self.debug_enabled = debug_enabled

    def start_activity_loop(self) -> None:
        """Main loop to keep the lesson active."""
        print("[INFO] Starting activity loop to keep lesson active...")

        if self.debug_enabled:
            utils.debug_dump(self.page, "before_activity_loop")

        iter_count = 0

        try:
            while True:
                iter_count += 1
                print(f"[LOOP] Iteration {iter_count}: Playing audio...")

                self._play_audio()
                self._wait_and_debug(50, iter_count)
                self._rewind_audio()
                self._pause_audio()
                self._toggle_modes()

                print("[LOOP] Cycle completed, repeating...")

        except KeyboardInterrupt:
            print("[INFO] Loop interrupted by user.")

    def _play_audio(self) -> None:
        """Play audio by clicking the play control."""
        try:
            self.page.locator("polygon").nth(3).click()
        except Exception:
            print("[WARN] Play control (polygon) not found in this iteration.")

    def _wait_and_debug(self, seconds: int, iteration: int) -> None:
        """Wait for specified seconds and optionally take debug screenshot."""
        time.sleep(seconds)

        if self.debug_enabled and iteration <= 3:
            try:
                utils.debug_dump(self.page, f"activity_iter_{iteration}")
            except Exception:
                pass

    def _rewind_audio(self) -> None:
        """Rewind audio by 10 seconds."""
        print("[LOOP] Rewinding 10 seconds...")
        try:
            self.page.get_by_text("10").click()
        except Exception:
            pass
        time.sleep(5)

    def _pause_audio(self) -> None:
        """Pause the audio."""
        print("[LOOP] Pausing...")
        try:
            self.page.locator("rect").nth(1).click()
        except Exception:
            pass
        time.sleep(5)

    def _toggle_modes(self) -> None:
        """Toggle between Read and Listen modes."""
        print("[LOOP] Secondary actions: Read and Listen...")
        try:
            self.page.get_by_text(re.compile(r"Leer|Read", re.I)).click()
            time.sleep(5)
            self.page.get_by_text(re.compile(r"Escuchar|Listen", re.I)).click()
        except Exception:
            pass
        time.sleep(5)
