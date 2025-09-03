"""Constants and action definitions for Rosetta Stone Bot."""

import re
from dataclasses import dataclass


def compile_case_insensitive(pattern: str) -> re.Pattern:
    """
    Utility function to compile regex patterns with case-insensitive flag.
    
    Args:
        pattern: The regex pattern string
        
    Returns:
        Compiled regex pattern with IGNORECASE flag
    """
    return re.compile(pattern, re.IGNORECASE)


@dataclass 
class CompiledPatterns:
    """Pre-compiled regex patterns for better performance."""
    
    # Login patterns
    SIGNIN = compile_case_insensitive(r"sign\s*in|iniciar\s*sesión|acceder|entrar|login")
    LOGIN_PAGE = compile_case_insensitive(r"login|signin|acceder|entrar|iniciar")

    # Cookie patterns
    COOKIE_ACCEPT = compile_case_insensitive(
        r"accept|agree|allow|ok|got\s*it|entendido|acept(ar|o)|permit(ir|o)|de\s*acuerdo"
    )

    # Navigation patterns
    FOUNDATIONS = compile_case_insensitive(r"foundations|fundamentos")
    BROWSE_CONTENT = compile_case_insensitive(
        r"^(explorar\s+todo\s+el\s+contenido|browse\s+all\s+content|explore\s+all\s+content)$"
    )
    CONTINUE_WITHOUT_VOICE = compile_case_insensitive(
        r"continuar\s+sin\s+voz|continue\s+without\s+(voice|speech)"
    )
    LISTEN = compile_case_insensitive(r"escuchar|listen")
    READ = compile_case_insensitive(r"leer|read")
    
    # Story completion patterns
    COMPLETION = compile_case_insensitive(r"completado|completed|finalizado|finished")
    NEXT_STORY = compile_case_insensitive(r"siguiente|next")
    STORIES_SECTION = compile_case_insensitive(r"^historias$|^stories$")


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
    FOUNDATIONS_PATTERNS = r"foundations|fundamentos"
    BROWSE_CONTENT_PATTERNS = (
        r"^(explorar\s+todo\s+el\s+contenido|browse\s+all\s+content|explore\s+all\s+content)$"
    )
    CONTINUE_WITHOUT_VOICE_PATTERNS = r"continuar\s+sin\s+voz|continue\s+without\s+(voice|speech)"
    LISTEN_PATTERNS = r"escuchar|listen"
    READ_PATTERNS = r"leer|read"
    
    # Story completion patterns
    COMPLETION_PATTERNS = r"completado|completed|finalizado|finished"
    NEXT_STORY_PATTERNS = r"siguiente|next"
    STORIES_SECTION_PATTERNS = r"^historias$|^stories$"


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
