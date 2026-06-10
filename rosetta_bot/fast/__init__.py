"""
Fast Stories usage-reporting capability.

Credits Stories hours directly via the ``app_usage`` API across N parallel
browser sessions, instead of playing stories in real time. Used as the primary
strategy by the orchestrator, with the full browser bot as fallback.
"""

from .config import FastReportConfig
from .result import FastReportResult
from .usage_api import UsageApiClient
from .dashboard import DashboardReader
from .runner import FastStoriesRunner

__all__ = [
    "FastReportConfig",
    "FastReportResult",
    "UsageApiClient",
    "DashboardReader",
    "FastStoriesRunner",
]
