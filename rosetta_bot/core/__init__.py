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
from .first_run import ensure_env_exists
from .paths import app_base_dir, auth_state_path, sanitize_account_key
from .login_guard import (
    MANUAL_LOGIN_HINT,
    find_login_blocker,
    is_kmsi_prompt,
    is_login_url,
)

__all__ = [
    "Timeouts",
    "WaitTimes",
    "URLs",
    "Logger",
    "LogLevel",
    "get_logger",
    "channel_candidates",
    "ensure_env_exists",
    "app_base_dir",
    "auth_state_path",
    "sanitize_account_key",
    "MANUAL_LOGIN_HINT",
    "find_login_blocker",
    "is_kmsi_prompt",
    "is_login_url",
]
