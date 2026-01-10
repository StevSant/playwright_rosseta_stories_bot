"""Debug service for screenshots and diagnostics."""

import re
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page

from ..core import Logger, get_logger


class DebugService:
    """
    Service for debugging and diagnostics.

    Handles screenshot capture, HTML dumps, and diagnostic information.

    Responsibility: Debug operations ONLY
    """

    DEFAULT_DEBUG_DIR = "debug"

    def __init__(
        self,
        page: Page,
        debug_dir: str = DEFAULT_DEBUG_DIR,
        enabled: bool = True,
        logger: Logger = None,
    ):
        """
        Initialize the debug service.

        Args:
            page: Playwright Page object
            debug_dir: Directory for debug output
            enabled: Whether debugging is enabled
            logger: Optional logger instance
        """
        self._page = page
        self._debug_dir = Path(debug_dir)
        self._enabled = enabled
        self._logger = logger or get_logger("Debug")
        self._counter = 0

        # Ensure debug directory exists
        if self._enabled:
            self._debug_dir.mkdir(exist_ok=True)
            self._load_counter()

    def _load_counter(self) -> None:
        """Load the persistent counter from file."""
        idx_file = self._debug_dir / ".dump_index"
        try:
            self._counter = int(idx_file.read_text(encoding="utf-8").strip() or "0")
        except Exception:
            self._counter = 0

    def _save_counter(self) -> None:
        """Save the counter to file."""
        idx_file = self._debug_dir / ".dump_index"
        try:
            idx_file.write_text(str(self._counter), encoding="utf-8")
        except Exception:
            pass

    def _sanitize_tag(self, tag: str) -> str:
        """Sanitize a tag for use in filenames."""
        return re.sub(r"[^0-9A-Za-z_.-]", "_", tag).strip("_")

    def dump(self, tag: str = "state") -> Optional[str]:
        """
        Create a debug dump with screenshot and page info.

        Args:
            tag: Tag for the dump filename

        Returns:
            Path to the screenshot if created, None otherwise
        """
        if not self._enabled or self._page is None:
            return None

        try:
            self._counter += 1
            self._save_counter()

            safe_tag = self._sanitize_tag(tag)
            base_name = (
                f"{self._counter}.{safe_tag}" if safe_tag else str(self._counter)
            )

            # Take screenshot
            screenshot_path = self._debug_dir / f"{base_name}.png"
            self._page.screenshot(path=str(screenshot_path), full_page=True)

            # Log page info
            self._log_page_info(base_name)

            self._logger.debug(f"Dump saved: {base_name}")
            return str(screenshot_path)

        except Exception as e:
            self._logger.warn(f"Debug dump failed: {e}")
            return None

    def _log_page_info(self, base_name: str) -> None:
        """Log page information for debugging."""
        try:
            info = [
                f"URL: {self._page.url}",
                f"Title: {self._page.title()}",
                f"Frames: {len(self._page.frames)}",
            ]

            for i, frame in enumerate(self._page.frames):
                try:
                    info.append(f"  [{i}] name={frame.name} url={frame.url}")
                except Exception:
                    pass

            # Save info file
            info_path = self._debug_dir / f"{base_name}.txt"
            info_path.write_text("\n".join(info), encoding="utf-8")

        except Exception:
            pass

    def screenshot(self, name: str) -> Optional[str]:
        """
        Take a simple screenshot.

        Args:
            name: Screenshot filename (without extension)

        Returns:
            Path to screenshot if successful, None otherwise
        """
        if not self._enabled:
            return None

        try:
            path = self._debug_dir / f"{name}.png"
            self._page.screenshot(path=str(path))
            return str(path)
        except Exception as e:
            self._logger.warn(f"Screenshot failed: {e}")
            return None

    def get_page_text(self, max_chars: int = 500) -> str:
        """
        Get visible text from the page.

        Args:
            max_chars: Maximum characters to return

        Returns:
            Page text truncated to max_chars
        """
        try:
            text = self._page.inner_text("body")
            return text[:max_chars]
        except Exception:
            return ""
