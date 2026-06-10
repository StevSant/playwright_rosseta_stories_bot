"""
Rosetta Stone Bot - Entry Point.

Runs the orchestrator: the fast Stories usage-reporting path first, with the
full Playwright browser bot as fallback when the fast path makes no progress.

Usage:
  uv run main.py              # uses .env
  uv run main.py .env_daniela # specific env file
"""

import sys

from dotenv import load_dotenv

from rosetta_bot import Orchestrator


def main() -> None:
    env_file = sys.argv[1] if len(sys.argv) > 1 else ".env"
    load_dotenv(env_file, override=True)

    Orchestrator.from_env().run()


if __name__ == "__main__":
    main()
