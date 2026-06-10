"""Reader for the learner dashboard (Stories hours readback)."""

import json
import urllib.request
from typing import Optional

from ..core import URLs


class DashboardReader:
    """
    Reads the learner dashboard to report total/eLearning hours before and
    after a run. Best-effort: returns ``None`` if the token/guid are missing
    or the request fails.
    """

    def __init__(self, user_agent: str = "Mozilla/5.0"):
        self._user_agent = user_agent

    def get_hours(self, access_token: str, user_guid: str) -> Optional[dict]:
        """
        Fetch dashboard hours.

        Returns ``{"name", "total_h", "elearn_h"}`` or ``None``.
        """
        if not access_token or not user_guid:
            return None

        req = urllib.request.Request(
            f"{URLs.DASHBOARD_BASE}/{user_guid}?skipLastUsageDate=true",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "User-Agent": self._user_agent,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                activities = data.get("allTimeActivities", {})
                return {
                    "name": data.get("name", "Unknown"),
                    "total_h": activities.get("totalTimeSpentMs", 0) / 3600000,
                    "elearn_h": activities.get("elearningTimeSpentMs", 0) / 3600000,
                }
        except Exception:
            return None
