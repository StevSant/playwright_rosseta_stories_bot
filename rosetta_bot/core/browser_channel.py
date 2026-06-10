"""Resolve which browser channel Playwright should launch.

Prefers a system-installed browser so a packaged .exe needs no
`playwright install`. Order: BROWSER_CHANNEL (default "chrome") -> "msedge"
(always present on Windows) -> None (Playwright's bundled Chromium).
"""

import os


def channel_candidates() -> list[str | None]:
    """Return browser channels to try, in order, de-duplicated."""
    preferred = os.getenv("BROWSER_CHANNEL", "chrome").strip() or None
    candidates: list[str | None] = []
    for channel in (preferred, "msedge", None):
        if channel not in candidates:
            candidates.append(channel)
    return candidates
