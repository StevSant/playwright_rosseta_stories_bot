"""
Fast Stories usage-reporting capability.

Credits Stories hours directly via the ``app_usage`` API across N parallel
browser sessions, instead of playing stories in real time. Used as the primary
strategy by the orchestrator, with the full browser bot as fallback.

Gradual-accumulation support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``StateStore`` persists per-account cumulative progress so the bot can be
invoked once or twice a day by Windows Task Scheduler and credit only a small
randomized slice of hours per run, reaching TARGET_HOURS over many weeks.

``compute_budget`` / ``SessionBudget`` determine how many seconds to credit
in a given invocation given the per-run and per-day caps from config.
"""

from .config import FastReportConfig
from .result import FastReportResult
from .session_budget import SessionBudget, compute_budget
from .state_store import StateStore
from .usage_api import UsageApiClient
from .dashboard import DashboardReader
from .runner import FastStoriesRunner

__all__ = [
    "FastReportConfig",
    "FastReportResult",
    "SessionBudget",
    "compute_budget",
    "StateStore",
    "UsageApiClient",
    "DashboardReader",
    "FastStoriesRunner",
]
