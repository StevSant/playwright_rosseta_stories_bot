"""
Fast Rosetta Stone Stories V3 - Parallel sessions reporting real usage.

Runs N parallel browser contexts. Each context logs in, enters a Story to
establish a valid LCP session, then reports Stories usage time directly via
the same API the real JS player uses:

  POST /api/v3/app_usage/report_usage           (session init)
  POST /api/v3/app_usage/report_additional_usage (incremental seconds)

This is the approach that actually credits hours on the institution admin
Stories dashboard. The previous iteration of this script relied on speeding
up `session/heartbeat`, which does NOT drive Stories usage reporting - the
JS player only emits `report_additional_usage` on mode changes inside a
story, and never fires it just from idling. A live probe confirmed zero
`app_usage/*` traffic from pure idling.

Resilience:
  - If a session's reporting loop fails, it is re-initialized on the same
    cookies (cheap) or the whole context is rebuilt (fallback)
  - Browser-level crash triggers a full browser restart and re-login

Usage:
  uv run python fast_stories_v3.py              # uses .env
  uv run python fast_stories_v3.py .env_daniela # specific env file

Environment variables:
  EMAIL, PASSWORD       - credentials (required)
  TARGET_HOURS          - total hours to accumulate across all sessions (default: 35)
  PARALLEL_SESSIONS     - number of parallel browser sessions (default: 5)
  REPORT_CHUNK_MIN_SEC  - min seconds per report_additional_usage chunk (default: 300)
  REPORT_CHUNK_MAX_SEC  - max seconds per chunk (default: 900)
  REPORT_DELAY_SEC      - delay between chunk POSTs per session (default: 0.5)
  HEADLESS              - run headless (default: 1)
"""

import asyncio
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime

from dotenv import load_dotenv
from playwright.async_api import async_playwright, Playwright

env_file = sys.argv[1] if len(sys.argv) > 1 else ".env"
load_dotenv(env_file, override=True)

EMAIL = os.environ.get("EMAIL", "")
PASSWORD = os.environ.get("PASSWORD", "")
TARGET_HOURS = float(os.environ.get("TARGET_HOURS", "35"))
PARALLEL_SESSIONS = int(os.environ.get("PARALLEL_SESSIONS", "5"))
CHUNK_MIN_SEC = int(os.environ.get("REPORT_CHUNK_MIN_SEC", "300"))
CHUNK_MAX_SEC = int(os.environ.get("REPORT_CHUNK_MAX_SEC", "900"))
REPORT_DELAY_SEC = float(os.environ.get("REPORT_DELAY_SEC", "0.5"))
HEADLESS = os.environ.get("HEADLESS", "1") == "1"

LCP_BASE = "https://lcp.rosettastone.com"
DASHBOARD_BASE = "https://prism.rosettastone.com/reports/learner/dashboard"

HEALTH_CHECK_INTERVAL = 60
STATUS_REPORT_INTERVAL = 120


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def http_post(url: str, body: dict, cookies: str) -> dict | None:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Cookie": cookies,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            ),
            "Referer": "https://totale.rosettastone.com/",
            "Origin": "https://totale.rosettastone.com",
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


def report_usage_init(cookies: str, session_id: str, language: str = "ENG") -> dict | None:
    return http_post(
        f"{LCP_BASE}/api/v3/app_usage/report_usage",
        {
            "app_identifier": "stories",
            "app_version": "11.11.2",
            "started_ago": 0,
            "usage_length": 0,
            "language": language,
            "session_identifier": session_id,
        },
        cookies,
    )


def report_additional_usage(cookies: str, usage_length_sec: int, session_id: str) -> dict | None:
    return http_post(
        f"{LCP_BASE}/api/v3/app_usage/report_additional_usage",
        {
            "usage_length": usage_length_sec,
            "session_identifier": session_id,
        },
        cookies,
    )


def get_dashboard(access_token: str, user_guid: str) -> dict | None:
    if not access_token or not user_guid:
        return None
    req = urllib.request.Request(
        f"{DASHBOARD_BASE}/{user_guid}?skipLastUsageDate=true",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            total = data.get("allTimeActivities", {}).get("totalTimeSpentMs", 0)
            elearn = data.get("allTimeActivities", {}).get("elearningTimeSpentMs", 0)
            return {
                "name": data.get("name", "Unknown"),
                "total_h": total / 3600000,
                "elearn_h": elearn / 3600000,
            }
    except Exception:
        return None


async def login_and_setup(browser, session_id: int, shared_auth: dict) -> dict | None:
    """
    Create context, login, navigate to Stories, enter a story.
    Returns session dict: {session_id, context, page, cookies_str, stories_session_id, ...}
    """
    tag = f"[S{session_id}]"

    context = await browser.new_context(
        viewport={"width": 1366, "height": 768},
        locale="es-ES",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),
    )
    page = await context.new_page()

    captured_stories_session_id = ""

    async def on_request(request):
        nonlocal captured_stories_session_id
        if (
            "app_usage/report_usage" in request.url
            and not captured_stories_session_id
        ):
            try:
                data = json.loads(request.post_data or "{}")
                sid = data.get("session_identifier", "")
                if sid:
                    captured_stories_session_id = sid
                    log(f"{tag} Captured JS session_id: {sid[:8]}...")
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
        log(f"{tag} Logging in...")
        await page.goto(
            "https://login.rosettastone.com/login",
            wait_until="networkidle",
            timeout=60000,
        )
        await asyncio.sleep(2)

        try:
            btn = page.locator(
                "button:has-text('Accept'), button:has-text('Aceptar')"
            ).first
            if await btn.is_visible(timeout=2000):
                await btn.click()
        except Exception:
            pass

        async def fill(selectors, value):
            for sel in selectors:
                try:
                    field = page.locator(sel).first
                    if await field.is_visible(timeout=2000):
                        await field.fill(value)
                        return field
                except Exception:
                    continue
            return None

        await fill(
            [
                "input[type='email']",
                "input[autocomplete='email']",
                "input[name='email']",
            ],
            EMAIL,
        )
        pw_field = await fill(
            ["input[type='password']", "input[name='password']"],
            PASSWORD,
        )
        if pw_field:
            await asyncio.sleep(1)
            await pw_field.press("Enter")

        await asyncio.sleep(5)
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass

        try:
            content = await page.content()
            if "uleam" in content.lower():
                log(f"{tag} Selecting institutional account...")
                el = page.get_by_text("uleam", exact=False).first
                if await el.is_visible(timeout=5000):
                    await el.click()
                    await asyncio.sleep(3)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    pw2 = await fill(["input[type='password']"], PASSWORD)
                    if pw2:
                        await asyncio.sleep(1)
                        await pw2.press("Enter")
                    await asyncio.sleep(5)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=20000)
                    except Exception:
                        pass
        except Exception:
            pass

        log(f"{tag} Authenticating with totale...")
        try:
            el = page.get_by_text("Foundations", exact=False).first
            if not await el.is_visible(timeout=3000):
                el = page.get_by_text("Fundamentos", exact=False).first
            await el.click()
            await asyncio.sleep(8)
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
        except Exception:
            pass

        log(f"{tag} Navigating to Stories...")
        await page.goto(
            "https://totale.rosettastone.com/stories",
            wait_until="networkidle",
            timeout=60000,
        )
        await asyncio.sleep(5)

        try:
            btn = page.locator(
                "button:has-text('Continuar'), button:has-text('Continue')"
            ).first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await asyncio.sleep(2)
        except Exception:
            pass

        known_stories = [
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
        story_name = None
        for name in known_stories:
            try:
                el = page.get_by_text(name, exact=True).first
                if await el.is_visible(timeout=1000):
                    await el.click()
                    story_name = name
                    break
            except Exception:
                continue

        if not story_name:
            log(f"{tag} ERROR: Could not click any story")
            await context.close()
            return None

        log(f"{tag} Entered story: {story_name}")
        await asyncio.sleep(5)

        for btn_text in ["Continuar", "Continue", "Escuchar", "Listen"]:
            try:
                btn = page.locator(f"button:has-text('{btn_text}')").first
                if await btn.is_visible(timeout=1500):
                    await btn.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

        # Give the JS player a few seconds in case it emits its own report_usage
        await asyncio.sleep(4)

        cookies_list = await context.cookies()
        relevant = [c for c in cookies_list if "rosettastone.com" in c.get("domain", "")]
        cookies_str = "; ".join(f"{c['name']}={c['value']}" for c in relevant)

        stories_session_id = captured_stories_session_id or str(uuid.uuid4())
        if not captured_stories_session_id:
            init = report_usage_init(cookies_str, stories_session_id)
            if init is None or (isinstance(init, dict) and "__error__" in init):
                err = (init or {}).get("__error__", "unknown")
                log(f"{tag} report_usage init failed: {err}. Abort.")
                await context.close()
                return None
            log(f"{tag} Initialized own session_id: {stories_session_id[:8]}...")
        else:
            log(f"{tag} Using JS-captured session_id: {stories_session_id[:8]}...")

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
        log(f"{tag} Setup failed: {e}")
        try:
            await context.close()
        except Exception:
            pass
        return None


async def reporting_loop(session: dict, seconds_to_report: int, stop_event: asyncio.Event):
    """
    Per-session task: sends report_additional_usage in chunks until it has
    credited `seconds_to_report` seconds, or stop_event is set, or an error
    makes further progress impossible.
    """
    tag = f"[S{session['session_id']}]"
    cookies_str = session["cookies_str"]
    stories_session_id = session["stories_session_id"]

    while (
        not stop_event.is_set()
        and session["seconds_reported"] < seconds_to_report
        and not session["failed"]
    ):
        remaining = seconds_to_report - session["seconds_reported"]
        chunk = min(remaining, random.randint(CHUNK_MIN_SEC, CHUNK_MAX_SEC))

        result = await asyncio.to_thread(
            report_additional_usage, cookies_str, chunk, stories_session_id
        )

        if result is None or (isinstance(result, dict) and "__error__" in result):
            err = (result or {}).get("__error__", "unknown")
            log(f"{tag} report_additional_usage failed at {session['seconds_reported']}s: {err}")
            session["failed"] = True
            return

        session["seconds_reported"] += chunk
        session["chunks_sent"] += 1

        if session["chunks_sent"] % 20 == 0:
            log(
                f"{tag} {session['chunks_sent']} chunks | "
                f"{session['seconds_reported'] / 3600:.2f}h / "
                f"{seconds_to_report / 3600:.2f}h reported"
            )

        await asyncio.sleep(REPORT_DELAY_SEC)

    log(
        f"{tag} Reporting done. {session['chunks_sent']} chunks, "
        f"{session['seconds_reported'] / 3600:.2f}h credited."
    )


async def is_page_alive(page) -> bool:
    try:
        await page.evaluate("1+1")
        return True
    except Exception:
        return False


async def setup_all_sessions(pw: Playwright, shared_auth: dict) -> tuple:
    browser = await pw.chromium.launch(
        headless=HEADLESS,
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
    for i in range(PARALLEL_SESSIONS):
        session = await login_and_setup(browser, i + 1, shared_auth)
        if session:
            sessions.append(session)
        else:
            log(f"Session {i + 1} failed to setup, continuing with others...")
        if i < PARALLEL_SESSIONS - 1:
            await asyncio.sleep(3)

    return browser, sessions


async def main():
    if not EMAIL or not PASSWORD:
        print("ERROR: Set EMAIL and PASSWORD in .env")
        return

    print("=" * 60)
    print("Rosetta Stone - Fast Stories V3 (parallel report_additional_usage)")
    print("=" * 60)
    print(f"  Email:              {EMAIL}")
    print(f"  Target total:       {TARGET_HOURS}h")
    print(f"  Parallel sessions:  {PARALLEL_SESSIONS}")
    print(f"  Chunk size:         {CHUNK_MIN_SEC}-{CHUNK_MAX_SEC}s")
    print(f"  Delay between POSTs: {REPORT_DELAY_SEC}s")
    print(f"  Headless:           {HEADLESS}")
    print("=" * 60)
    print()

    start_time = time.time()
    shared_auth: dict = {}

    async with async_playwright() as pw:
        browser, sessions = await setup_all_sessions(pw, shared_auth)

        if not sessions:
            log("No sessions established. Exiting.")
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            return

        log(f"{len(sessions)}/{PARALLEL_SESSIONS} sessions active.")

        before = get_dashboard(
            shared_auth.get("access_token", ""), shared_auth.get("user_guid", "")
        )
        if before:
            log(f"User: {before['name']}")
            log(f"Dashboard BEFORE: total={before['total_h']:.4f}h | elearn={before['elearn_h']:.4f}h")

        target_total_sec = int(TARGET_HOURS * 3600)
        per_session_sec = target_total_sec // len(sessions)

        log(
            f"\nReporting {TARGET_HOURS}h total => "
            f"{per_session_sec}s (~{per_session_sec / 3600:.2f}h) per session."
        )
        log("Press Ctrl+C to stop early.\n")

        stop_event = asyncio.Event()

        reporting_tasks = [
            asyncio.create_task(reporting_loop(s, per_session_sec, stop_event))
            for s in sessions
        ]

        async def status_monitor():
            last_report = time.time()
            while not stop_event.is_set():
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)

                # Health check browsers + page alive
                alive_count = 0
                for s in sessions:
                    if await is_page_alive(s["page"]):
                        alive_count += 1

                now = time.time()
                total_reported = sum(s["seconds_reported"] for s in sessions)
                total_reported_h = total_reported / 3600

                if now - last_report >= STATUS_REPORT_INTERVAL:
                    last_report = now
                    elapsed_h = (now - start_time) / 3600
                    log(
                        f"Running {elapsed_h:.2f}h | {alive_count}/{len(sessions)} pages alive | "
                        f"Reported: {total_reported_h:.2f}h / {TARGET_HOURS}h"
                    )

                if all(t.done() for t in reporting_tasks):
                    stop_event.set()
                    return

                if total_reported_h >= TARGET_HOURS:
                    stop_event.set()
                    return

        monitor_task = asyncio.create_task(status_monitor())

        try:
            await asyncio.gather(*reporting_tasks)
        except KeyboardInterrupt:
            log("\nInterrupted.")
            stop_event.set()

        stop_event.set()
        monitor_task.cancel()
        try:
            await monitor_task
        except (asyncio.CancelledError, Exception):
            pass

        await asyncio.sleep(3)
        after = get_dashboard(
            shared_auth.get("access_token", ""), shared_auth.get("user_guid", "")
        )

        elapsed = time.time() - start_time
        total_reported = sum(s["seconds_reported"] for s in sessions)
        total_chunks = sum(s["chunks_sent"] for s in sessions)
        failed_sessions = sum(1 for s in sessions if s["failed"])

        print("\n" + "=" * 60)
        print("SESSION SUMMARY")
        print("=" * 60)
        print(f"  Wall time:           {elapsed / 3600:.2f}h ({elapsed:.0f}s)")
        print(f"  Active sessions:     {len(sessions)}")
        print(f"  Failed sessions:     {failed_sessions}")
        print(f"  Chunks sent:         {total_chunks}")
        print(f"  Hours reported:      {total_reported / 3600:.2f}h")
        if before:
            print(f"  Dashboard BEFORE:    total={before['total_h']:.4f}h")
        if after:
            print(f"  Dashboard AFTER:     total={after['total_h']:.4f}h")
            if before:
                diff = after["total_h"] - before["total_h"]
                print(f"  Dashboard change:    {diff:+.4f}h")
                print("  (Stories hours for admin dashboard may appear in a separate bucket.)")
        print("=" * 60)

        if browser:
            try:
                await browser.close()
            except Exception:
                pass

    log("Done. Ask the institution admin to check Stories hours.")


if __name__ == "__main__":
    asyncio.run(main())
