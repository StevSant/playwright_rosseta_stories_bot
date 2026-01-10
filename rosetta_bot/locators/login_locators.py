"""Locators for the Login page."""

import re
from dataclasses import dataclass
from typing import Pattern, List


def _compile_pattern(pattern: str) -> Pattern[str]:
    """Compile a regex pattern with case-insensitive flag."""
    return re.compile(pattern, re.IGNORECASE)


@dataclass(frozen=True)
class LoginLocators:
    """Locators for the login page elements."""

    # URLs
    LOGIN_URL: str = "https://login.rosettastone.com/login"

    # Email field selectors (multiple for resilience)
    EMAIL_SELECTORS: str = (
        "input[type='email'], input[name='email'], input#email, "
        "input[autocomplete='username'], input[autocomplete='email'], "
        "input[placeholder='Email address'], [data-qa='Email']"
    )
    EMAIL_FALLBACK_SELECTORS: str = (
        "input[type='text'][name='email'], "
        "input[type='text'][autocomplete='username']"
    )

    # Password field selectors
    PASSWORD_SELECTORS: str = (
        "input[type='password'], input[name='password'], input#password, "
        "input[autocomplete='current-password'], [data-qa='Password'], "
        "input[placeholder='Password']"
    )

    # Submit button selectors
    SUBMIT_BUTTON: str = "[data-qa='SignInButton'], button[type='submit']"

    # Sign in button patterns
    SIGNIN_PATTERN: Pattern[str] = _compile_pattern(
        r"sign\s*in|iniciar\s*sesión|acceder|entrar|login"
    )

    # Login page detection patterns
    LOGIN_PAGE_PATTERN: Pattern[str] = _compile_pattern(
        r"login|signin|acceder|entrar|iniciar"
    )

    # Institutional account selectors
    INSTITUTIONAL_SELECTORS: List[str] = (
        "text=uleam",
        "[data-testid*='uleam']",
        "button:has-text('uleam')",
        "div:has-text('uleam')",
        "span:has-text('uleam')",
    )
