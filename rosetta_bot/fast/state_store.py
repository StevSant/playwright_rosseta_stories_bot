"""
Per-account cumulative progress state store.

Persists to a small JSON file so the scheduler can call this bot once or
twice a day and let hours accumulate gradually toward TARGET_HOURS.

File path: ``<STATE_DIR>/<account_key>.json``

Schema::

    {
        "cumulative_seconds": 12345,
        "today_seconds":      600,
        "today_date":         "2026-06-10",
        "last_run":           "2026-06-10T14:32:00"
    }
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class StateStore:
    """
    Read/write per-account progress state from a JSON file.

    ``account_key`` is used as the file stem (unsafe characters are
    replaced with underscores, e.g. ``e1315205631@live.uleam.edu.ec``
    → ``e1315205631_live_uleam_edu_ec``).
    """

    def __init__(self, state_dir: str, account_key: str):
        safe_key = "".join(c if c.isalnum() or c in "-_" else "_" for c in account_key)
        self._path = Path(state_dir) / f"{safe_key}.json"

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def load(self) -> dict:
        """
        Return the current state dict.

        Keys (all guaranteed present after this call):
          - ``cumulative_seconds`` (int)
          - ``today_seconds`` (int)
          - ``today_date`` (str, ISO date "YYYY-MM-DD")
          - ``last_run`` (str, ISO datetime or "")
        """
        raw = self._read_raw()
        today = self._today_str()

        # Reset daily counter if the stored date differs from today.
        if raw.get("today_date") != today:
            raw["today_seconds"] = 0
            raw["today_date"] = today

        raw.setdefault("cumulative_seconds", 0)
        raw.setdefault("last_run", "")
        return raw

    def save(self, state: dict) -> None:
        """Persist *state* to disk (atomic: write then replace)."""
        state["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def add_seconds(self, seconds: int) -> dict:
        """
        Atomically load state, add *seconds* to both cumulative and today
        counters, persist, and return the updated state.
        """
        state = self.load()
        state["cumulative_seconds"] = state.get("cumulative_seconds", 0) + seconds
        state["today_seconds"] = state.get("today_seconds", 0) + seconds
        self.save(state)
        return state

    @property
    def path(self) -> Path:
        """Path to the underlying JSON file (useful for logging)."""
        return self._path

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _read_raw(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    @staticmethod
    def _today_str() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
