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

Gradual-accumulation design
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Each invocation credits only a small, randomized amount of hours (bounded by
SESSION_HOURS_MIN/MAX and MAX_HOURS_PER_DAY), then exits.  Cumulative progress
is persisted to a per-account JSON state file (see :mod:`~.state_store`).
Running once or twice a day via Windows Task Scheduler spreads TARGET_HOURS
over many weeks like a real learner.

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

from ..core import (
    MANUAL_LOGIN_HINT,
    Logger,
    URLs,
    auth_state_path,
    channel_candidates,
    find_login_blocker,
    get_logger,
    is_kmsi_prompt,
    is_login_url,
)
from ..locators import StoriesLocators
from .config import FastReportConfig
from .dashboard import DashboardReader
from .result import FastReportResult
from .session_budget import compute_budget
from .state_store import StateStore
from .usage_api import UsageApiClient

HEALTH_CHECK_INTERVAL = 60
STATUS_REPORT_INTERVAL = 120
STORY_LOAD_TIMEOUT_SEC = 60
STORY_LOAD_POLL_SEC = 2


class FastStoriesRunner:
    """Runs parallel Stories usage-reporting sessions."""

    def __init__(self, config: FastReportConfig, logger: Optional[Logger] = None):
        self._config = config
        self._logger = logger or get_logger("FastStories")
        self._api = UsageApiClient(config.user_agent)
        self._dashboard = DashboardReader()
        self._locators = StoriesLocators()
        # Times each story has been claimed by a session, keyed by story name.
        # Sessions pick the least-claimed story so they spread across stories
        # instead of all piling onto the first visible one.
        self._story_claims: dict = {}

    # ==================== Public API ====================

    async def run(self) -> FastReportResult:
        """
        Credit a small, randomized slice of hours for this invocation.

        The per-run amount is bounded by SESSION_HOURS_MIN/MAX and the
        remaining daily and cumulative budgets.  Progress is persisted so
        successive scheduler runs accumulate gradually toward TARGET_HOURS.
        """
        cfg = self._config
        self._log_header()

        # ── State & budget ────────────────────────────────────────────────
        account_key = cfg.state_key or cfg.email
        store = StateStore(cfg.state_dir, account_key)

        # Seed an account-specific RNG so different accounts randomize
        # independently even when invoked at the same clock time.
        account_seed = int.from_bytes(account_key.encode()[:8], "little")
        account_rng = random.Random(account_seed ^ int(time.time()))

        state = store.load()
        budget = compute_budget(
            state=state,
            target_seconds=int(cfg.target_hours * 3600),
            session_min_sec=int(cfg.session_hours_min * 3600),
            session_max_sec=int(cfg.session_hours_max * 3600),
            max_daily_sec=int(cfg.max_hours_per_day * 3600),
            rng=account_rng,
            human_mode=cfg.human_mode,
        )

        cumulative_h = state.get("cumulative_seconds", 0) / 3600
        self._logger.info(
            f"State: cumulative={cumulative_h:.3f}h / {cfg.target_hours}h target. "
            f"Budget: {budget.reason}"
        )

        if budget.this_run_seconds <= 0:
            self._logger.info("Nothing to credit this run. Exiting without launching browser.")
            return FastReportResult()

        # ── Browser sessions ──────────────────────────────────────────────
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

            # Distribute this-run budget across sessions (not the full target).
            this_run_sec = budget.this_run_seconds
            per_session_sec = this_run_sec // len(sessions)
            self._logger.info(
                f"This run: {this_run_sec / 3600:.3f}h total => {per_session_sec}s "
                f"(~{per_session_sec / 3600:.3f}h) per session. Ctrl+C to stop early."
            )

            stop_event = asyncio.Event()
            reporting_tasks = [
                asyncio.create_task(
                    self._reporting_loop(s, per_session_sec, stop_event, account_rng)
                )
                for s in sessions
            ]
            monitor_task = asyncio.create_task(
                self._status_monitor(
                    sessions,
                    reporting_tasks,
                    stop_event,
                    start_time,
                    this_run_hours=this_run_sec / 3600,
                )
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

        # ── Persist progress ──────────────────────────────────────────────
        total_reported_sec = int(result.hours_reported * 3600)
        updated = store.add_seconds(total_reported_sec)
        self._logger.info(
            f"State updated: cumulative={updated['cumulative_seconds'] / 3600:.3f}h, "
            f"today={updated['today_seconds'] / 3600:.3f}h  [{store.path}]"
        )

        self._logger.info("Done. Ask the institution admin to check Stories hours.")
        return result

    # ==================== Session Setup ====================

    async def _setup_all_sessions(self, pw: Playwright, shared_auth: dict) -> tuple:
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
        ]
        # Prefer a system browser (chrome -> msedge -> bundled Chromium) so a
        # packaged .exe needs no `playwright install`.
        browser = None
        last_error: Optional[Exception] = None
        for channel in channel_candidates():
            try:
                browser = await pw.chromium.launch(
                    headless=self._config.headless, args=launch_args, channel=channel
                )
                break
            except Exception as exc:
                last_error = exc
        if browser is None:
            raise RuntimeError(
                "Could not launch a browser. Install Chrome/Edge or run "
                "'playwright install chromium'."
            ) from last_error

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
        setup_start = time.time()

        # Reuse a previously saved login session when available: it skips the
        # whole login flow and avoids re-triggering Microsoft's new-device
        # verification on machines that haven't logged in before.
        auth_state = auth_state_path(cfg.email)
        context_kwargs = {
            "viewport": {"width": 1366, "height": 768},
            "locale": "es-ES",
            "user_agent": cfg.user_agent,
        }
        if auth_state.exists():
            self._logger.info(f"{tag} Reusing saved login session: {auth_state}")
            context_kwargs["storage_state"] = str(auth_state)

        context = await browser.new_context(**context_kwargs)
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

            if is_login_url(page.url):
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
                await self._handle_stay_signed_in(page)
                # Fail loudly here (MFA / CAPTCHA / wrong password) instead of
                # blundering on to Stories with a logged-out page.
                await self._ensure_authenticated(page, tag)
            else:
                self._logger.info(f"{tag} Already authenticated (restored session).")

            await self._authenticate_totale(page, tag)

            self._logger.info(f"{tag} Navigating to Stories...")
            await page.goto(URLs.STORIES, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)
            if is_login_url(page.url):
                raise RuntimeError(
                    f"Redirected back to login when opening Stories ({page.url}). "
                    f"The session is not authenticated. {MANUAL_LOGIN_HINT}"
                )

            # Login confirmed - persist the session for future runs.
            auth_state.parent.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(auth_state))
            await self._click_first_button(page, ["Continuar", "Continue"], timeout=3000)
            await self._wait_for_stories(page, tag)

            story_name = await self._enter_distinct_story(page, tag)
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

            # Realistic started_ago: actual seconds spent on browser setup.
            # This tells the server the story started when the browser did,
            # not at the exact instant of the first API call.
            started_ago_sec = int(time.time() - setup_start)

            if not captured_session_id:
                init = await asyncio.to_thread(
                    self._api.report_usage_init,
                    cookies_str,
                    stories_session_id,
                    cfg.language,
                    started_ago_sec,
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
                "started_ago": started_ago_sec,
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
        self,
        session: dict,
        seconds_to_report: int,
        stop_event: asyncio.Event,
        rng: random.Random,
    ) -> None:
        """
        Send report_additional_usage in chunks until the per-run budget is
        credited for this session.

        Delays between POSTs are jittered between
        ``report_delay_min_sec`` and ``report_delay_max_sec`` using the
        shared per-account RNG so timing differs across accounts.
        """
        cfg = self._config
        tag = f"[S{session['session_id']}]"

        # The first chunk size doubles as a realistic ``started_ago`` value:
        # it tells the server the story began that many seconds ago, which is
        # plausible because we actually waited for browser setup before hitting
        # the API.
        first_chunk = min(seconds_to_report, rng.randint(cfg.chunk_min_sec, cfg.chunk_max_sec))
        session["started_ago"] = first_chunk

        while (
            not stop_event.is_set()
            and session["seconds_reported"] < seconds_to_report
            and not session["failed"]
        ):
            remaining = seconds_to_report - session["seconds_reported"]
            chunk = min(remaining, rng.randint(cfg.chunk_min_sec, cfg.chunk_max_sec))

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

            if session["chunks_sent"] % 10 == 0:
                self._logger.info(
                    f"{tag} {session['chunks_sent']} chunks | "
                    f"{session['seconds_reported'] / 3600:.3f}h / "
                    f"{seconds_to_report / 3600:.3f}h reported"
                )

            # Fast mode fires POSTs back-to-back; human mode jitters the pacing.
            if cfg.human_mode:
                delay = rng.uniform(cfg.report_delay_min_sec, cfg.report_delay_max_sec)
                await asyncio.sleep(delay)

        self._logger.info(
            f"{tag} Reporting done. {session['chunks_sent']} chunks, "
            f"{session['seconds_reported'] / 3600:.3f}h credited."
        )

    async def _status_monitor(
        self,
        sessions: list,
        reporting_tasks: list,
        stop_event: asyncio.Event,
        start_time: float,
        this_run_hours: float = 0.0,
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
                    f"Reported: {total_reported_h:.3f}h / {this_run_hours:.3f}h this run"
                )

            if all(t.done() for t in reporting_tasks):
                stop_event.set()
                return
            if this_run_hours > 0 and total_reported_h >= this_run_hours:
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

    async def _handle_stay_signed_in(self, page) -> None:
        """Accept Microsoft's 'Stay signed in?' (KMSI) prompt if shown."""
        try:
            if not is_kmsi_prompt(await page.inner_text("body")):
                return
        except Exception:
            return

        try:
            checkbox = page.locator("#KmsiCheckboxField").first
            if await checkbox.is_visible(timeout=1500):
                await checkbox.check()
        except Exception:
            pass

        for selector in (
            "#idSIButton9",
            "input[type='submit'][value='Yes']",
            "input[type='submit'][value='Sí']",
            "button:has-text('Yes')",
            "button:has-text('Sí')",
        ):
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=1500):
                    await btn.click()
                    await asyncio.sleep(2)
                    return
            except Exception:
                continue

    async def _ensure_authenticated(self, page, tag: str) -> None:
        """
        Raise with a clear reason if we are still stuck on a login page.

        Microsoft may interrupt the institutional flow on a new device/IP
        with a verification screen (MFA, code, CAPTCHA) that no selector in
        this runner can complete; surface that instead of timing out later.
        """
        deadline = time.time() + 15
        while time.time() < deadline:
            if not is_login_url(page.url):
                return
            await asyncio.sleep(1)

        blocker = None
        try:
            blocker = find_login_blocker(await page.inner_text("body"))
        except Exception:
            pass

        detail = f" Blocking screen: {blocker}." if blocker else ""
        raise RuntimeError(
            f"Login did not complete - still on {page.url}.{detail} {MANUAL_LOGIN_HINT}"
        )

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

    async def _wait_for_stories(self, page, tag: str) -> None:
        """The story list renders well after networkidle; poll until tiles exist."""
        deadline = time.time() + STORY_LOAD_TIMEOUT_SEC
        while time.time() < deadline:
            try:
                if await page.locator(self._locators.STORY_TITLE).count() > 0:
                    return
            except Exception:
                pass
            await asyncio.sleep(STORY_LOAD_POLL_SEC)
        self._logger.warn(f"{tag} Story list did not render within {STORY_LOAD_TIMEOUT_SEC}s")

    async def _enter_distinct_story(self, page, tag: str) -> Optional[str]:
        """
        Click a story, preferring ones no other session has claimed yet.

        Stories are discovered from the page's story tiles; the hardcoded
        known-name list is only a fallback. Candidates are tried least-claimed
        first, so each session lands on a different story until all are taken,
        then claims wrap around evenly.
        """
        candidates = await self._discover_stories(page)
        if not candidates:
            self._logger.warn(f"{tag} No story tiles found, falling back to known names")
            candidates = [
                (name, page.get_by_text(name, exact=True).first)
                for name in self._locators.KNOWN_STORIES
            ]

        candidates.sort(key=lambda c: self._story_claims.get(c[0], 0))

        for name, el in candidates:
            try:
                if not await el.is_visible(timeout=1000):
                    continue
                await el.scroll_into_view_if_needed()
                await el.click()
                self._story_claims[name] = self._story_claims.get(name, 0) + 1
                return name
            except Exception:
                continue
        return None

    async def _discover_stories(self, page) -> list:
        """Return [(story_name, locator)] for every story tile on the page."""
        stories = []
        seen = set()
        try:
            titles = page.locator(self._locators.STORY_TITLE)
            texts = await titles.all_inner_texts()
            for i, text in enumerate(texts):
                name = text.strip()
                if name and name not in seen:
                    seen.add(name)
                    stories.append((name, titles.nth(i)))
        except Exception:
            pass
        return stories

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
        self._logger.info(f"  Mode:              {'HUMAN (gradual)' if cfg.human_mode else 'FAST (full target in one run)'}")
        self._logger.info(f"  Target total:      {cfg.target_hours}h")
        if cfg.human_mode:
            self._logger.info(f"  Session window:    {cfg.session_hours_min}-{cfg.session_hours_max}h / run")
            self._logger.info(f"  Daily cap:         {cfg.max_hours_per_day}h / day")
        self._logger.info(f"  Parallel sessions: {cfg.parallel_sessions}")
        self._logger.info(f"  Chunk size:        {cfg.chunk_min_sec}-{cfg.chunk_max_sec}s")
        if cfg.human_mode:
            self._logger.info(f"  Post delay:        {cfg.report_delay_min_sec}-{cfg.report_delay_max_sec}s (jittered)")
        else:
            self._logger.info("  Post delay:        none (back-to-back)")
        self._logger.info(f"  Headless:          {cfg.headless}")
        self._logger.info(f"  State dir:         {cfg.state_dir}")
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
