"""Navigation service for Rosetta Stone lessons."""

import re

from playwright.sync_api import Page

from . import utils


class LessonNavigator:
    """Handles navigation through Rosetta Stone lessons."""

    def __init__(self, page: Page):
        self.page = page

    def navigate_to_lesson(self) -> None:
        """Navigate to the specific lesson to play and take key screenshots."""
        self._enter_foundations()
        self._browse_all_content()
        self._select_lesson()
        self._enter_specific_lesson()
        self._continue_without_voice()
        self._select_listen_mode()
        self._setup_dialog_handling()

    def _enter_foundations(self) -> None:
        """Enter the Foundations/Fundamentos section."""
        print("[INFO] Entering 'Foundations/Fundamentos'...")
        self.page.get_by_text(re.compile(r"Foundations|Fundamentos", re.I)).click()
        utils.debug_dump(self.page, "foundations")

    def _browse_all_content(self) -> None:
        """Browse all content in the section."""
        print("[INFO] Exploring all content / Browse all content...")
        self.page.get_by_text(
            re.compile(
                r"Explorar todo el contenido|Browse all content|Explore all content",
                re.I,
            )
        ).click()
        utils.debug_dump(self.page, "browse_all_content")

    def _select_lesson(self) -> None:
        """Select the second lesson."""
        print("[INFO] Selecting second lesson...")
        self.page.locator("a").nth(1).click()
        utils.debug_dump(self.page, "selected_second_lesson")

    def _enter_specific_lesson(self) -> None:
        """Enter the specific lesson."""
        print("[INFO] Clicking on specific lesson...")
        self.page.locator(
            "div:nth-child(6) > div:nth-child(2) > .css-3bo236 > div > "
            ".css-djy551 > .css-a9mqkc > .css-vl4mjm"
        ).click()
        utils.debug_dump(self.page, "entered_specific_lesson")

    def _continue_without_voice(self) -> None:
        """Continue without voice recognition."""
        print("[INFO] Waiting and clicking 'Continue without voice'...")
        cont_btn = self.page.get_by_role("button").filter(
            has_text=re.compile(r"Continuar sin voz|Continue without voice", re.I)
        )
        cont_btn.first.wait_for(state="visible", timeout=60000)
        cont_btn.first.click()
        utils.debug_dump(self.page, "continue_without_voice")

    def _select_listen_mode(self) -> None:
        """Select Listen/Escuchar mode."""
        print("[INFO] Selecting 'Listen/Escuchar'...")
        self.page.get_by_text(re.compile(r"Escuchar|Listen", re.I)).click()
        utils.debug_dump(self.page, "listen_mode")

    def _setup_dialog_handling(self) -> None:
        """Setup automatic dialog dismissal."""
        self.page.on("dialog", lambda dialog: dialog.dismiss())
        print("[INFO] Popup dialogs configured to auto-dismiss.")
