"""Centralized locators for all pages and components."""

from .login_locators import LoginLocators
from .stories_locators import StoriesLocators
from .lesson_locators import LessonLocators
from .launchpad_locators import LaunchpadLocators
from .common_locators import CommonLocators

__all__ = [
    "LoginLocators",
    "StoriesLocators",
    "LessonLocators",
    "LaunchpadLocators",
    "CommonLocators",
]
