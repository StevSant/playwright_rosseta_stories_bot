"""Result of a fast Stories reporting run."""

from dataclasses import dataclass


@dataclass
class FastReportResult:
    """
    Outcome of ``FastStoriesRunner.run()``.

    The orchestrator uses ``active_sessions`` and ``hours_reported`` to decide
    whether to fall back to the full browser bot.
    """

    active_sessions: int = 0
    hours_reported: float = 0.0
    failed_sessions: int = 0
    chunks_sent: int = 0
