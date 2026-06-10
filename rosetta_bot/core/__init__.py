"""
Core module containing fundamental building blocks.

This module provides:
- Timeouts: Timeout constants in milliseconds
- WaitTimes: Wait time constants in seconds
- URLs: Application URL constants
- Logger: Centralized logging service
- get_logger: Factory function for creating loggers
"""

from .timeouts import Timeouts
from .wait_times import WaitTimes
from .urls import URLs
from .logger import Logger, LogLevel, get_logger
from .browser_channel import channel_candidates

__all__ = [
    "Timeouts",
    "WaitTimes",
    "URLs",
    "Logger",
    "LogLevel",
    "get_logger",
    "channel_candidates",
]
