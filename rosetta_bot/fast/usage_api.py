"""HTTP client for the Rosetta Stone Stories ``app_usage`` reporting API."""

import json
import urllib.error
import urllib.request
from typing import Optional

from ..core import URLs


class UsageApiClient:
    """
    Thin client over the two ``app_usage`` endpoints the JS Stories player uses:

      - ``report_usage``            initializes a tracking session
      - ``report_additional_usage`` credits incremental seconds

    Calls are blocking (``urllib``); the runner invokes them via
    ``asyncio.to_thread`` so they don't block the event loop.

    Every method returns the decoded JSON response, or a dict containing an
    ``__error__`` key on failure (never raises).
    """

    def __init__(
        self,
        user_agent: str,
        *,
        app_identifier: str = "stories",
        app_version: str = "11.11.2",
    ):
        self._user_agent = user_agent
        self._app_identifier = app_identifier
        self._app_version = app_version

    def report_usage_init(
        self, cookies: str, session_id: str, language: str = "ENG"
    ) -> Optional[dict]:
        """Initialize a Stories usage session (called once on entering a story)."""
        return self._post(
            URLs.REPORT_USAGE,
            {
                "app_identifier": self._app_identifier,
                "app_version": self._app_version,
                "started_ago": 0,
                "usage_length": 0,
                "language": language,
                "session_identifier": session_id,
            },
            cookies,
        )

    def report_additional_usage(
        self, cookies: str, usage_length_sec: int, session_id: str
    ) -> Optional[dict]:
        """Credit ``usage_length_sec`` additional seconds to an existing session."""
        return self._post(
            URLs.REPORT_ADDITIONAL_USAGE,
            {
                "usage_length": usage_length_sec,
                "session_identifier": session_id,
            },
            cookies,
        )

    def _post(self, url: str, body: dict, cookies: str) -> Optional[dict]:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Cookie": cookies,
                "User-Agent": self._user_agent,
                "Referer": URLs.TOTALE_REFERER,
                "Origin": URLs.TOTALE_ORIGIN,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            try:
                body_text = e.read().decode()[:300]
            except Exception:
                body_text = ""
            return {"__error__": f"HTTP {e.code}: {body_text}"}
        except Exception as e:
            return {"__error__": f"HTTP error: {e}"}
