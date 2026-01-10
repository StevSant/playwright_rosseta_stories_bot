"""Locators for the Launchpad page."""

import re
from dataclasses import dataclass
from typing import Pattern


def _compile_pattern(pattern: str) -> Pattern[str]:
    """Compile a regex pattern with case-insensitive flag."""
    return re.compile(pattern, re.IGNORECASE)


@dataclass(frozen=True)
class LaunchpadLocators:
    """Locators for the launchpad and navigation elements."""

    # URLs
    LAUNCHPAD_URL: str = "https://login.rosettastone.com/launchpad"

    # Foundations section
    FOUNDATIONS_PATTERN: Pattern[str] = _compile_pattern(r"foundations|fundamentos")

    # Browse content
    BROWSE_CONTENT_PATTERN: Pattern[str] = _compile_pattern(
        r"^(explorar\s+todo\s+el\s+contenido|browse\s+all\s+content|explore\s+all\s+content)$"
    )

    # Stories section
    STORIES_SECTION: str = '[data-qa="stories-section"]'
    SEE_ALL_LINK: str = '[data-qa="explore_section_see_all_link"]'

    # Lesson selection
    SPECIFIC_LESSON_PATTERN: Pattern[str] = _compile_pattern(
        r"A Visit to Hollywood|Una visita a Hollywood"
    )
    BOOK_COVER_PREFIX: str = '[data-qa^="BookCover-"]'
