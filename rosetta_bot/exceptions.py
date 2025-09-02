"""Custom exceptions for Rosetta Stone Bot."""


class RosettaBotError(Exception):
    """Base exception for Rosetta Bot errors."""

    pass


class BrowserError(RosettaBotError):
    """Raised when browser operations fail."""

    pass


class AuthenticationError(RosettaBotError):
    """Raised when authentication fails."""

    pass


class NavigationError(RosettaBotError):
    """Raised when navigation operations fail."""

    pass


class ConfigurationError(RosettaBotError):
    """Raised when configuration is invalid."""

    pass
