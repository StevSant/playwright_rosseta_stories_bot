"""Centralized logging service."""

from enum import Enum
from typing import Optional
from datetime import datetime


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    LOOP = "LOOP"


class Logger:
    """
    Centralized logging service.
    
    Provides consistent logging across all modules with optional
    timestamps and configurable log levels.
    
    Attributes:
        name: Logger name (usually module/class name)
        show_timestamp: Whether to include timestamps in logs
        min_level: Minimum log level to display
    """
    
    # Class-level log level priority
    _LEVEL_PRIORITY = {
        LogLevel.DEBUG: 0,
        LogLevel.LOOP: 1,
        LogLevel.INFO: 2,
        LogLevel.WARN: 3,
        LogLevel.ERROR: 4,
    }

    def __init__(
        self,
        name: str = "",
        show_timestamp: bool = False,
        min_level: LogLevel = LogLevel.DEBUG
    ):
        """
        Initialize the logger.
        
        Args:
            name: Logger name for identification
            show_timestamp: Include timestamps in output
            min_level: Minimum level to log
        """
        self._name = name
        self._show_timestamp = show_timestamp
        self._min_level = min_level

    def log(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        """
        Log a message with the specified level.
        
        Args:
            message: Message to log
            level: Log level
        """
        if self._LEVEL_PRIORITY[level] < self._LEVEL_PRIORITY[self._min_level]:
            return
        
        parts = []
        
        if self._show_timestamp:
            parts.append(datetime.now().strftime("%H:%M:%S"))
        
        parts.append(f"[{level.value}]")
        
        if self._name:
            parts.append(f"[{self._name}]")
        
        parts.append(message)
        
        print(" ".join(parts))

    def debug(self, message: str) -> None:
        """Log a debug message."""
        self.log(message, LogLevel.DEBUG)

    def info(self, message: str) -> None:
        """Log an info message."""
        self.log(message, LogLevel.INFO)

    def warn(self, message: str) -> None:
        """Log a warning message."""
        self.log(message, LogLevel.WARN)

    def error(self, message: str) -> None:
        """Log an error message."""
        self.log(message, LogLevel.ERROR)

    def loop(self, message: str) -> None:
        """Log a loop iteration message."""
        self.log(message, LogLevel.LOOP)


# Global default logger
default_logger = Logger()


def get_logger(name: str = "", show_timestamp: bool = False) -> Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        show_timestamp: Include timestamps
        
    Returns:
        Logger instance
    """
    return Logger(name=name, show_timestamp=show_timestamp)
