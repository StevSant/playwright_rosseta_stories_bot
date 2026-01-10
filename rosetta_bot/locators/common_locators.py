"""Common locators shared across multiple pages."""

import re
from dataclasses import dataclass
from typing import Pattern


def _compile_pattern(pattern: str) -> Pattern[str]:
    """Compile a regex pattern with case-insensitive flag."""
    return re.compile(pattern, re.IGNORECASE)


@dataclass(frozen=True)
class CommonLocators:
    """Locators for common elements shared across pages."""

    # Audio modal
    AUDIO_MODAL_PROMPT_BUTTON: str = '[data-qa="PromptButton"]'
    AUDIO_MODAL_CONTINUE: str = '[data-qa="continue"]'

    # Generic buttons
    CONTINUE_BUTTON_PATTERN: Pattern[str] = _compile_pattern(r"Continuar|Continue")

    # Cookie consent
    COOKIE_CLOSE_BUTTON: str = "button[aria-label='Close'], [data-testid='close']"
    COOKIE_ACCEPT_PATTERN: Pattern[str] = _compile_pattern(
        r"accept|agree|allow|ok|got\s*it|entendido|acept(ar|o)|permit(ir|o)|de\s*acuerdo"
    )

    # Voice modal
    CONTINUE_WITHOUT_VOICE_PATTERN: Pattern[str] = _compile_pattern(
        r"continuar\s+sin\s+voz|continue\s+without\s+(voice|speech)"
    )

    # Mode selection
    LISTEN_PATTERN: Pattern[str] = _compile_pattern(r"escuchar|listen")
    READ_PATTERN: Pattern[str] = _compile_pattern(r"leer|read")
