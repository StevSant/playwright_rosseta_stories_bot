from dotenv import load_dotenv
import os
from playwright.sync_api import sync_playwright

from rosetta_bot import RosettaStoneBot


def main():
    load_dotenv()

    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    headless_env = os.getenv("PLAYWRIGHT_HEADLESS", "1")
    headless = headless_env.lower() not in ("0", "false", "no")

    with sync_playwright() as playwright:
        bot = RosettaStoneBot(email, password, slow_mo=500, headless=headless)
        bot.launch_browser(playwright)
        bot.login()
        bot.navigate_to_lesson()
        bot.activity_loop()
        bot.close_browser()


if __name__ == "__main__":
    main()
