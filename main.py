"""
Rosetta Stone Bot - Entry Point

This module provides the main entry point for running the Rosetta Stone
automation bot in different modes.

Modes:
    1. Infinite Stories Loop: Continuously processes all stories
    2. Standard Lesson: Runs a lesson once with activity loop
    3. Infinite Lesson Loop: Repeats a specific lesson infinitely
"""

from enum import Enum

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from rosetta_bot import RosettaStoneBot, AppConfig


class BotMode(Enum):
    """Available bot operation modes."""

    INFINITE_STORIES = "infinite_stories"
    STANDARD_LESSON = "standard_lesson"
    INFINITE_LESSON = "infinite_lesson"


def main(mode: BotMode = BotMode.INFINITE_LESSON) -> None:
    """
    Run the Rosetta Stone Bot in the specified mode.

    Args:
        mode: The operation mode for the bot
    """
    # Load environment variables
    load_dotenv(".env_oliver")

    # Create configuration from environment variables
    config = AppConfig.from_env()

    print(f"[INFO] Starting Rosetta Stone Bot in {mode.value} mode...")

    with sync_playwright() as playwright:
        bot = RosettaStoneBot(config)

        if mode == BotMode.INFINITE_STORIES:
            # Mode 1: Infinite stories loop
            bot.run_infinite_stories_loop(playwright)

        elif mode == BotMode.STANDARD_LESSON:
            # Mode 2: Standard lesson (run once)
            bot.run(playwright)

        elif mode == BotMode.INFINITE_LESSON:
            # Mode 3: Infinite lesson loop
            bot.run_infinite_lesson_loop(playwright)


if __name__ == "__main__":
    # Change the mode here as needed:
    # - BotMode.INFINITE_STORIES: Loop through all stories
    # bot_mode = BotMode.INFINITE_ALL_STORIES
    # - BotMode.STANDARD_LESSON: Run a single lesson
    # bot_mode = BotMode.STANDARD_LESSON
    # - BotMode.INFINITE_LESSON: Loop a specific lesson
    bot_mode = BotMode.INFINITE_LESSON

    main(mode=bot_mode)
