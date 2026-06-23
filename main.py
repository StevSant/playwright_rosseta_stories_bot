"""
Rosetta Stone Bot - Entry Point.

Runs the orchestrator: the fast Stories usage-reporting path first, with the
full Playwright browser bot as fallback when the fast path makes no progress.

Usage:
  uv run main.py              # uses .env
  uv run main.py .env_daniela # specific env file
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

from rosetta_bot import Orchestrator
from rosetta_bot.core import app_base_dir, ensure_env_exists


def _default_env_file() -> str:
    """Default .env location: next to the .exe when frozen, else project root."""
    return str(app_base_dir() / ".env")


def main() -> None:
    env_file = sys.argv[1] if len(sys.argv) > 1 else _default_env_file()
    ensure_env_exists(Path(env_file))
    load_dotenv(env_file, override=True)

    Orchestrator.from_env().run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"\nError: {exc}")
    finally:
        if getattr(sys, "frozen", False):
            input("\nPresiona Enter para cerrar...")
