"""Browser management for the Rosetta Stone Bot."""

from pathlib import Path
from typing import Optional

from playwright.sync_api import (
    Playwright,
    Browser,
    BrowserContext,
    Page,
)

from .config import BrowserConfig
from .core import channel_candidates


class BrowserManager:
    """Manages browser lifecycle and configuration."""

    def __init__(self, config: BrowserConfig):
        self.config = config
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def launch(self, playwright: Playwright) -> Page:
        """Launch browser and return the main page."""
        self._launch_browser(playwright)
        self._create_context()
        self._create_page()

        if not self.page:
            raise RuntimeError("Failed to create page")

        return self.page

    def _launch_browser(self, playwright: Playwright) -> None:
        """Initialize the browser, preferring a system-installed channel.

        Tries channels in order (chrome -> msedge -> bundled Chromium) so a
        packaged .exe works without `playwright install`.
        """
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-default-browser-check",
            "--disable-dev-shm-usage",
        ]
        last_error: Optional[Exception] = None
        for channel in channel_candidates():
            try:
                self.browser = playwright.chromium.launch(
                    headless=self.config.headless,
                    slow_mo=self.config.slow_mo,
                    args=args,
                    channel=channel,
                )
                return
            except Exception as exc:
                last_error = exc
        # Last resort: bundled Chromium with no extra flags
        try:
            self.browser = playwright.chromium.launch(
                headless=self.config.headless, slow_mo=self.config.slow_mo
            )
        except Exception as exc:
            raise RuntimeError(
                "Could not launch a browser. Install Chrome/Edge or run "
                "'playwright install chromium'."
            ) from (last_error or exc)

    def _create_context(self) -> None:
        """Create browser context with realistic settings."""
        if not self.browser:
            raise RuntimeError("Browser not launched")

        context_kwargs = {
            "permissions": [],
            "accept_downloads": True,
            "user_agent": self.config.user_agent,
            "locale": self.config.locale,
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            },
        }

        state_path = self.config.storage_state_path
        if state_path and Path(state_path).exists():
            print(f"[INFO] Reusing saved login session: {state_path}")
            context_kwargs["storage_state"] = state_path

        self.context = self.browser.new_context(**context_kwargs)

    def save_storage_state(self) -> None:
        """Persist cookies/localStorage so later runs can skip the login."""
        state_path = self.config.storage_state_path
        if not (self.context and state_path):
            return
        try:
            Path(state_path).parent.mkdir(parents=True, exist_ok=True)
            self.context.storage_state(path=state_path)
            print(f"[INFO] Login session saved: {state_path}")
        except Exception as exc:
            print(f"[WARN] Could not save login session: {exc}")

    def _create_page(self) -> None:
        """Create the main page."""
        if not self.context:
            raise RuntimeError("Browser context not created")

        self.page = self.context.new_page()

    def close(self) -> None:
        """Close browser, context and page."""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        print("[INFO] Browser closed.")
