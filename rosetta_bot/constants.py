"""Constants and action definitions for Rosetta Stone Bot."""

from dataclasses import dataclass


@dataclass
class Selectors:
    """CSS selectors used throughout the application."""

    # Login selectors
    EMAIL_SELECTORS = [
        "input[type='email']",
        "input[name='email']",
        "input#email",
        "input[autocomplete='username']",
        "input[autocomplete='email']",
        "input[placeholder='Email address']",
        "[data-qa='Email']",
        "input[type='text'][name='email']",
        "input[type='text'][autocomplete='username']",
    ]

    PASSWORD_SELECTORS = [
        "input[type='password']",
        "input[name='password']",
        "input#password",
        "input[autocomplete='current-password']",
        "[data-qa='Password']",
        "input[placeholder='Password']",
    ]

    LOGIN_BUTTON_SELECTORS = [
        "[data-qa='SignInButton']",
        "button[type='submit']",
        "input[type='submit']",
    ]

    # Cookie consent selectors
    COOKIE_ACCEPT_SELECTORS = ["button[aria-label='Close']", "[data-testid='close']"]

    # Lesson activity selectors
    PLAY_CONTROL_SELECTOR = "polygon:nth-child(4)"  # nth(3) in 0-based indexing
    PAUSE_CONTROL_SELECTOR = "rect:nth-child(2)"  # nth(1) in 0-based indexing
    REWIND_SELECTOR = "10"  # Text-based selector


@dataclass
class URLs:
    """URLs used by the application."""

    LOGIN_URL = "https://login.rosettastone.com/login"


@dataclass
class TextPatterns:
    """Regular expression patterns for text matching."""

    # Login patterns
    SIGNIN_PATTERNS = r"sign\s*in|iniciar\s*sesión|acceder|entrar|login"
    LOGIN_PAGE_PATTERNS = r"login|signin|acceder|entrar|iniciar"

    # Cookie patterns
    COOKIE_ACCEPT_PATTERNS = (
        r"accept|agree|allow|ok|got\s*it|entendido|acept(ar|o)|"
        r"permit(ir|o)|de\s*acuerdo"
    )

    # Navigation patterns
    FOUNDATIONS_PATTERNS = r"Foundations|Fundamentos"
    BROWSE_CONTENT_PATTERNS = (
        r"Explorar todo el contenido|Browse all content|Explore all content"
    )
    CONTINUE_WITHOUT_VOICE_PATTERNS = r"Continuar sin voz|Continue without voice"
    LISTEN_PATTERNS = r"Escuchar|Listen"
    READ_PATTERNS = r"Leer|Read"


@dataclass
class Timeouts:
    """Timeout values in milliseconds."""

    DEFAULT_TIMEOUT = 5000
    LONG_TIMEOUT = 10000
    VERY_LONG_TIMEOUT = 60000
    SHORT_TIMEOUT = 3000
    VERY_SHORT_TIMEOUT = 1500
    COOKIE_TIMEOUT = 2000


@dataclass
class WaitTimes:
    """Wait times in seconds for various operations."""

    ACTIVITY_CYCLE = 50
    SHORT_WAIT = 5
    VERY_SHORT_WAIT = 2
