"""Timeout constants in milliseconds for Playwright operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Timeouts:
    """
    Timeout values in milliseconds for various operations.

    These are used for Playwright wait operations and should be
    adjusted based on network conditions and page complexity.
    """

    # Very short operations (UI updates)
    VERY_SHORT: int = 1500
    VERY_SHORT_TIMEOUT: int = 1500

    # Short operations (element visibility)
    SHORT: int = 3000
    SHORT_TIMEOUT: int = 3000

    # Default operations (most interactions)
    DEFAULT: int = 5000
    DEFAULT_TIMEOUT: int = 5000

    # Long operations (page loads)
    LONG: int = 10000
    LONG_TIMEOUT: int = 10000

    # Very long operations (complex navigations)
    VERY_LONG: int = 60000
    VERY_LONG_TIMEOUT: int = 60000

    # Cookie banner specific
    COOKIE: int = 2000
    COOKIE_TIMEOUT: int = 2000
