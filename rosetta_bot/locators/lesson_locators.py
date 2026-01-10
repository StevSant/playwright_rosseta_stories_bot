"""Locators for the Lesson page."""

import re
from dataclasses import dataclass
from typing import Pattern


def _compile_pattern(pattern: str) -> Pattern[str]:
    """Compile a regex pattern with case-insensitive flag."""
    return re.compile(pattern, re.IGNORECASE)


@dataclass(frozen=True)
class LessonLocators:
    """Locators for the lesson activity page elements."""

    # Audio controls
    PLAY_CONTROL: str = "polygon"
    PLAY_CONTROL_INDEX: int = 3
    PAUSE_CONTROL: str = "rect"
    PAUSE_CONTROL_INDEX: int = 1
    REWIND_TEXT: str = "10"

    # Lesson completion indicators
    COMPLETION_PATTERN: Pattern[str] = _compile_pattern(
        r"Completado|Completed|Terminado"
    )
    NEXT_LESSON_PATTERN: Pattern[str] = _compile_pattern(
        r"Siguiente lección|Next lesson"
    )
    CONTINUE_PATTERN: Pattern[str] = _compile_pattern(r"Continuar|Continue")

    # Restart controls
    RESTART_PATTERN: Pattern[str] = _compile_pattern(
        r"Repetir|Replay|Reiniciar|Restart"
    )
