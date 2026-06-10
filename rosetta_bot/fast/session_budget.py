"""
Per-run hour budget calculation.

Given the loaded state and the config caps, determines exactly how many
seconds this invocation should credit — or 0 if the goal is already
reached / today's daily cap is exhausted.
"""

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class SessionBudget:
    """
    Outcome of :func:`compute_budget`.

    ``this_run_seconds`` is the number of seconds to credit this run.
    Zero means "nothing to do — skip the browser launch entirely."

    ``reason`` is a human-readable string explaining the result (for logging).
    """

    this_run_seconds: int
    reason: str


def compute_budget(
    state: dict,
    target_seconds: int,
    session_min_sec: int,
    session_max_sec: int,
    max_daily_sec: int,
    rng: Optional[random.Random] = None,
) -> SessionBudget:
    """
    Compute how many seconds to credit in this run.

    Args:
        state:            Dict from :class:`~rosetta_bot.fast.StateStore`.load().
        target_seconds:   Cumulative goal in seconds (TARGET_HOURS * 3600).
        session_min_sec:  Minimum seconds per run (SESSION_HOURS_MIN * 3600).
        session_max_sec:  Maximum seconds per run (SESSION_HOURS_MAX * 3600).
        max_daily_sec:    Daily cap in seconds (MAX_HOURS_PER_DAY * 3600).
        rng:              Optional :class:`random.Random` instance (for
                          reproducible tests or per-account seeding).

    Returns:
        A :class:`SessionBudget` with the approved seconds and a reason string.
    """
    _rng = rng or random.Random()

    cumulative = int(state.get("cumulative_seconds", 0))
    today = int(state.get("today_seconds", 0))

    remaining_total = target_seconds - cumulative
    if remaining_total <= 0:
        return SessionBudget(
            this_run_seconds=0,
            reason=f"Goal already reached ({cumulative / 3600:.2f}h >= {target_seconds / 3600:.2f}h).",
        )

    remaining_today = max_daily_sec - today
    if remaining_today <= 0:
        return SessionBudget(
            this_run_seconds=0,
            reason=f"Daily cap reached ({today / 3600:.2f}h credited today, cap={max_daily_sec / 3600:.2f}h).",
        )

    # Desired amount for this run (randomized within session window).
    desired = _rng.randint(session_min_sec, session_max_sec)

    # Clamp to remaining total and daily budget.
    approved = min(desired, remaining_total, remaining_today)

    return SessionBudget(
        this_run_seconds=approved,
        reason=(
            f"Approved {approved / 3600:.3f}h "
            f"(desired={desired / 3600:.3f}h, "
            f"remaining_total={remaining_total / 3600:.3f}h, "
            f"remaining_today={remaining_today / 3600:.3f}h)."
        ),
    )
