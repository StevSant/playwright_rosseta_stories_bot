"""
Fast Stories runner.

Opens N parallel browser contexts. Each context logs in, enters a Story to
establish a valid LCP session, then reports Stories usage time directly via the
same API the real JS player uses:

  POST /api/v3/app_usage/report_usage            (session init)
  POST /api/v3/app_usage/report_additional_usage (incremental seconds)

This is the approach that actually credits hours on the institution admin
Stories dashboard. Speeding up ``session/heartbeat`` does NOT drive Stories
usage reporting - the JS player only emits ``report_additional_usage`` on mode
changes inside a story, never from idling (confirmed by a live probe).

The session setup, per-session reporting loop, and health monitor are kept
together here because they form one tightly-coupled async flow. The reusable,
independently-testable pieces (the API client, dashboard reader, config, and
result) live in their own modules.
"""

import asyncio
import json
import random
import time
import uuid
from typing import Optional

from playwright.async_api import async_playwright, Playwright

from ..core import Logger, URLs, get_logger
from .config import FastReportConfig
from .dashboard import DashboardReader
from .result import FastReportResult
from .usage_api import UsageApiClient

HEALTH_CHECK_INTERVAL = 60
STATUS_REPORT_INTERVAL = 120

# Stories known to exist for the target curriculum; we click the first match.
KNOWN_STORIES = [
    "A Man Is Walking",
    "Driving",
    "Maria and Rob: The Cat in the Tree",
    "Road Trip: Goodbye!",
    "The Big Yellow Sun",
    "The Boy from Hana",
    "The Small Farm",
    "Cats",
    "Hello from San Francisco",
]


class FastStoriesRunner:
    """Runs parallel Stories usage-reporting sessions."""

    def __init__(self, config: FastReportConfig, logger: Optional[Logger] = None):
        self._config = config
        self._logger = logger or get_logger("FastStories")
        self._api = UsageApiClient(config.user_agent)
        self._dashboard = DashboardReader()

    # ==================== Public API ====================

    async def run(self) -> FastReportResult:
        """
        Run all parallel reporting sessions until the target hours are credited,
        a stop is requested, or progress becomes impossible.
        """
        cfg = self._config
        self._log_header()

        start_time = time.time()
        shared_auth: dict = {}

        async with async_playwright() as pw:
            browser, sessions = await self._setup_all_sessions(pw, shared_auth)

            if not sessions:
                self._logger.warn("No sessions established. Exiting.")
                await self._close_browser(browser)
                return FastReportResult()

            self._logger.info(f"{len(sessions)}/{cfg.parallel_sessions} sessions active.")

            before = self._dashboard.get_hours(
                shared_auth.get("access_token", ""), shared_auth.get("user_guid", "")
            )
            if before:
                self._logger.info(f"User: {before['name']}")
                self._logger.info(
                    f"Dashboard BEFORE: total={before['total_h']:.4f}h | "
                    f"elearn={before['elearn_h']:.4f}h"
                )

            target_total_sec = int(cfg.target_hours * 3600)
            per_session_sec = target_total_sec // len(sessions)
            self._logger.info(
                f"Reporting {cfg.target_hours}h total => {per_session_sec}s "
                f"(~{per_session_sec / 3600:.2f}h) per session. Ctrl+C to stop early."
            )

            stop_event = asyncio.Event()
            reporting_tasks = [
                asyncio.create_task(self._reporting_loop(s, per_session_sec, stop_event))
                for s in sessions
            ]
            monitor_task = asyncio.create_task(
                self._status_monitor(sessions, reporting_tasks, stop_event, start_time)
            )

            try:
                await asyncio.gather(*reporting_tasks)
            except KeyboardInterrupt:
                self._logger.warn("Interrupted.")

            stop_event.set()
            monitor_task.cancel()
            try:
                await monitor_task
            except (asyncio.CancelledError, Exception):
                pass

            await asyncio.sleep(3)
            after = self._dashboard.get_hours(
                shared_auth.get("access_token", ""), shared_auth.get("user_guid", "")
            )

            result = self._summarize(sessions, start_time, before, after)
            await self._close_browser(browser)

        self._logger.info("Done. Ask the institution admin to check Stories hours.")
        return result

    # ==================== Session Setup ====================

    async def _setup_all_sessions(self, pw: Playwright, shared_auth: dict) -> tuple:
        browser = await pw.chromium.launch(
            headless=self._config.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
            ],
        )

        sessions = []
        for i in range(self._config.parallel_sessions):
            session = await self._login_and_setup(browser, i + 1, shared_auth)
            if session:
                sessions.append(session)
            else:
                self._logger.warn(f"Session {i + 1} failed to setup, continuing...")
            if i < self._config.parallel_sessions - 1:
                await asyncio.sleep(3)

        return browser, sessions

    async def _login_and_setup(
        self, browser, session_id: int, shared_auth: dict
    ) -> Optional[dict]:
        """Create context, login, navigate to Stories, enter a story."""
        cfg = self._config
        tag = f"[S{session_id}]"

        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="es-ES",
            user_agent=cfg.user_agent,
        )
        page = await context.new_page()

        captured_session_id = ""

        async def on_request(request):
            nonlocal captured_session_id
            if "app_usage/report_usage" in request.url and not captured_session_id:
                try:
                    data = json.loads(request.post_data or "{}")
                    sid = data.get("session_identifier", "")
                    if sid:
                        captured_session_id = sid
                        self._logger.info(f"{tag} Captured JS session_id: {sid[:8]}...")
                except Exception:
                    pass

        async def on_response(response):
            if "authentication/login" in response.url:
                try:
                    body = await response.json()
                    if "auth_data" in body and not shared_auth.get("access_token"):
                        shared_auth["access_token"] = body["auth_data"].get("access_token", "")
                        shared_auth["user_guid"] = body["auth_data"].get("userId", "")
                except Exception:
                    pass

        page.on("request", lambda r: asyncio.ensure_future(on_request(r)))
        page.on("response", lambda r: asyncio.ensure_future(on_response(r)))

        try:
            self._logger.info(f"{tag} Logging in...")
            await page.goto(URLs.LOGIN, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)

            await self._dismiss_cookie_banner(page)

            await self._fill_first(
                page,
                ["input[type='email']", "input[autocomplete='email']", "input[name='email']"],
                cfg.email,
            )
            pw_field = await self._fill_first(
                page, ["input[type='password']", "input[name='password']"], cfg.password
            )
            if pw_field:
                await asyncio.sleep(1)
                await pw_field.press("Enter")

            await asyncio.sleep(5)
            await self._wait_idle(page, 20000)

            await self._handle_institutional_account(page, tag)
            await self._authenticate_totale(page, tag)

            self._logger.info(f"{tag} Navigating to Stories...")
            await page.goto(URLs.STORIES, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)
            await self._click_first_button(page, ["Continuar", "Continue"], timeout=3000)

            story_name = await self._enter_known_story(page)
            if not story_name:
                self._logger.error(f"{tag} Could not click any story")
                await context.close()
                return None

            self._logger.info(f"{tag} Entered story: {story_name}")
            await asyncio.sleep(5)
            for label in ["Continuar", "Continue", "Escuchar", "Listen"]:
                await self._click_first_button(page, [label], timeout=1500)
            # Give the JS player a moment in case it emits its own report_usage.
            await asyncio.sleep(4)

            cookies_str = await self._collect_cookies(context)
            stories_session_id = captured_session_id or str(uuid.uuid4())

            if not captured_session_id:
                init = await asyncio.to_thread(
                    self._api.report_usage_init, cookies_str, stories_session_id, cfg.language
                )
                if init is None or (isinstance(init, dict) and "__error__" in init):
                    err = (init or {}).get("__error__", "unknown")
                    self._logger.error(f"{tag} report_usage init failed: {err}. Abort.")
                    await context.close()
                    return None
                self._logger.info(f"{tag} Initialized own session_id: {stories_session_id[:8]}...")
            else:
                self._logger.info(
                    f"{tag} Using JS-captured session_id: {stories_session_id[:8]}..."
                )

            return {
                "session_id": session_id,
                "context": context,
                "page": page,
                "story": story_name,
                "cookies_str": cookies_str,
                "stories_session_id": stories_session_id,
                "seconds_reported": 0,
                "chunks_sent": 0,
                "failed": False,
            }

        except Exception as e:
            self._logger.error(f"{tag} Setup failed: {e}")
            try:
                await context.close()
            except Exception:
                pass
            return None

    # ==================== Reporting ====================

    async def _reporting_loop(
        self, session: dict, seconds_to_report: int, stop_event: asyncio.Event
    ) -> None:
        """Send report_additional_usage in chunks until the target is credited."""
        cfg = self._config
        tag = f"[S{session['session_id']}]"

        while (
            not stop_event.is_set()
            and session["seconds_reported"] < seconds_to_report
            and not session["failed"]
        ):
            remaining = seconds_to_report - session["seconds_reported"]
            chunk = min(remaining, random.randint(cfg.chunk_min_sec, cfg.chunk_max_sec))

            result = await asyncio.to_thread(
                self._api.report_additional_usage,
                session["cookies_str"],
                chunk,
                session["stories_session_id"],
            )

            if result is None or (isinstance(result, dict) and "__error__" in result):
                err = (result or {}).get("__error__", "unknown")
                self._logger.error(
                    f"{tag} report_additional_usage failed at "
                    f"{session['seconds_reported']}s: {err}"
                )
                session["failed"] = True
                return

            session["seconds_reported"] += chunk
            session["chunks_sent"] += 1

            if session["chunks_sent"] % 20 == 0:
                self._logger.info(
                    f"{tag} {session['chunks_sent']} chunks | "
                    f"{session['seconds_reported'] / 3600:.2f}h / "
                    f"{seconds_to_report / 3600:.2f}h reported"
                )

            await asyncio.sleep(cfg.report_delay_sec)

        self._logger.info(
            f"{tag} Reporting done. {session['chunks_sent']} chunks, "
            f"{session['seconds_reported'] / 3600:.2f}h credited."
        )

    async def _status_monitor(
        self,
        sessions: list,
        reporting_tasks: list,
        stop_event: asyncio.Event,
        start_time: float,
    ) -> None:
        last_report = time.time()
        while not stop_event.is_set():
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

            alive_count = sum(1 for s in sessions if await self._is_page_alive(s["page"]))
            now = time.time()
            total_reported_h = sum(s["seconds_reported"] for s in sessions) / 3600

            if now - last_report >= STATUS_REPORT_INTERVAL:
                last_report = now
                self._logger.info(
                    f"Running {(now - start_time) / 3600:.2f}h | "
                    f"{alive_count}/{len(sessions)} pages alive | "
                    f"Reported: {total_reported_h:.2f}h / {self._config.target_hours}h"
                )

            if all(t.done() for t in reporting_tasks):
                stop_event.set()
                return
            if total_reported_h >= self._config.target_hours:
                stop_event.set()
                return

    # ==================== Helpers ====================

    async def _fill_first(self, page, selectors, value):
        for sel in selectors:
            try:
                field = page.locator(sel).first
                if await field.is_visible(timeout=2000):
                    await field.fill(value)
                    return field
            except Exception:
                continue
        return None

    async def _click_first_button(self, page, labels, timeout: int) -> bool:
        selector = ", ".join(f"button:has-text('{label}')" for label in labels)
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=timeout):
                await btn.click()
                await asyncio.sleep(1)
                return True
        except Exception:
            pass
        return False

    async def _dismiss_cookie_banner(self, page) -> None:
        await self._click_first_button(page, ["Accept", "Aceptar"], timeout=2000)

    async def _wait_idle(self, page, timeout: int) -> None:
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception:
            pass

    async def _handle_institutional_account(self, page, tag: str) -> None:
        try:
            content = await page.content()
            if "uleam" not in content.lower():
                return
            self._logger.info(f"{tag} Selecting institutional account...")
            el = page.get_by_text("uleam", exact=False).first
            if not await el.is_visible(timeout=5000):
                return
            await el.click()
            await asyncio.sleep(3)
            await self._wait_idle(page, 10000)
            pw2 = await self._fill_first(page, ["input[type='password']"], self._config.password)
            if pw2:
                await asyncio.sleep(1)
                await pw2.press("Enter")
            await asyncio.sleep(5)
            await self._wait_idle(page, 20000)
        except Exception:
            pass

    async def _authenticate_totale(self, page, tag: str) -> None:
        self._logger.info(f"{tag} Authenticating with totale...")
        try:
            el = page.get_by_text("Foundations", exact=False).first
            if not await el.is_visible(timeout=3000):
                el = page.get_by_text("Fundamentos", exact=False).first
            await el.click()
            await asyncio.sleep(8)
            await self._wait_idle(page, 20000)
        except Exception:
            pass

    async def _enter_known_story(self, page) -> Optional[str]:
        for name in KNOWN_STORIES:
            try:
                el = page.get_by_text(name, exact=True).first
                if await el.is_visible(timeout=1000):
                    await el.click()
                    return name
            except Exception:
                continue
        return None

    async def _collect_cookies(self, context) -> str:
        cookies_list = await context.cookies()
        relevant = [c for c in cookies_list if "rosettastone.com" in c.get("domain", "")]
        return "; ".join(f"{c['name']}={c['value']}" for c in relevant)

    async def _is_page_alive(self, page) -> bool:
        try:
            await page.evaluate("1+1")
            return True
        except Exception:
            return False

    async def _close_browser(self, browser) -> None:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass

    def _log_header(self) -> None:
        cfg = self._config
        self._logger.info("=" * 60)
        self._logger.info("Fast Stories (parallel report_additional_usage)")
        self._logger.info(f"  Email:             {cfg.email}")
        self._logger.info(f"  Target total:      {cfg.target_hours}h")
        self._logger.info(f"  Parallel sessions: {cfg.parallel_sessions}")
        self._logger.info(f"  Chunk size:        {cfg.chunk_min_sec}-{cfg.chunk_max_sec}s")
        self._logger.info(f"  Headless:          {cfg.headless}")
        self._logger.info("=" * 60)

    def _summarize(self, sessions, start_time, before, after) -> FastReportResult:
        elapsed = time.time() - start_time
        total_reported = sum(s["seconds_reported"] for s in sessions)
        total_chunks = sum(s["chunks_sent"] for s in sessions)
        failed = sum(1 for s in sessions if s["failed"])

        self._logger.info("=" * 60)
        self._logger.info("SESSION SUMMARY")
        self._logger.info(f"  Wall time:       {elapsed / 3600:.2f}h ({elapsed:.0f}s)")
        self._logger.info(f"  Active sessions: {len(sessions)}")
        self._logger.info(f"  Failed sessions: {failed}")
        self._logger.info(f"  Chunks sent:     {total_chunks}")
        self._logger.info(f"  Hours reported:  {total_reported / 3600:.2f}h")
        if before:
            self._logger.info(f"  Dashboard BEFORE: total={before['total_h']:.4f}h")
        if after:
            self._logger.info(f"  Dashboard AFTER:  total={after['total_h']:.4f}h")
            if before:
                self._logger.info(
                    f"  Dashboard change: {after['total_h'] - before['total_h']:+.4f}h"
                )
        self._logger.info("=" * 60)

        return FastReportResult(
            active_sessions=len(sessions),
            hours_reported=total_reported / 3600,
            failed_sessions=failed,
            chunks_sent=total_chunks,
        )
