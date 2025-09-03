import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from rosetta_bot import RosettaStoneBot, AppConfig


def main():
    # Load .env file only if EMAIL is not already set (not in Docker)
    if not os.getenv("EMAIL"):
        load_dotenv(dotenv_path=".env_oliver")

    # Create configuration from environment variables
    config = AppConfig.from_env()

    # Run the bot - puedes cambiar entre los diferentes modos aquí
    with sync_playwright() as playwright:
        bot = RosettaStoneBot(config)

        # Modo 1: Bucle infinito de historias (NUEVO)
        bot.run_infinite_stories_loop(playwright)

        # Modo 2: Lección tradicional original
        # bot.run(playwright)


if __name__ == "__main__":
    main()
