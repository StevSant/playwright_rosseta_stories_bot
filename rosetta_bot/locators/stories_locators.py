"""Locators for the Stories page."""

import re
from dataclasses import dataclass
from typing import Pattern, List


def _compile_pattern(pattern: str) -> Pattern[str]:
    """Compile a regex pattern with case-insensitive flag."""
    return re.compile(pattern, re.IGNORECASE)


@dataclass(frozen=True)
class StoriesLocators:
    """Locators for the stories page elements."""

    # URLs
    STORIES_URL: str = "https://totale.rosettastone.com/stories"

    # Story cards
    STORY_LINKS: str = "a[href*='/stories/']"

    # Story detection patterns
    STORIES_SECTION_PATTERN: Pattern[str] = _compile_pattern(r"^historias$|^stories$")

    # Completion indicators
    COMPLETION_PATTERN: Pattern[str] = _compile_pattern(
        r"completado|completed|finalizado|finished"
    )
    NEXT_STORY_PATTERN: Pattern[str] = _compile_pattern(r"siguiente|next")

    # Known story names for Unit 1
    KNOWN_STORIES: List[str] = (
        "A Man Is Walking",
        "Driving",
        "Maria and Rob: The Cat in the Tree",
        "Road Trip: Goodbye!",
        "Robotics Team: The New Student",
        "The Big Yellow Sun",
        "The Boy from Hana",
        "The Small Farm",
        "Cats",
        "He Loves Her, She Loves Him",
        "Hello from San Francisco",
        "A Visit to Hollywood",
    )

    # Audio player controls
    PLAY_BUTTON: str = "polygon"
    PLAY_BUTTON_INDEX: int = 3
    CIRCLE_BUTTON: str = "circle"
