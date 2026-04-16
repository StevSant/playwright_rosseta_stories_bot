"""
Fast Rosetta Stone Stories V3 - Parallel sessions + accelerated heartbeats.

Runs N parallel browser contexts, each accumulating Stories time via
heartbeats. The session/start response is intercepted to lower the
heartbeat interval so the JS player beats faster than normal.

Resilience:
  - If a single page dies but the browser is alive, re-creates that session
  - If the browser process crashes (all pages die), launches a new browser
    and re-establishes all sessions automatically
  - Health checks every 60s, status reports every 5 min

Usage:
  uv run python fast_stories_v3.py              # uses .env
  uv run python fast_stories_v3.py .env_daniela # specific env file

Environment variables:
  EMAIL, PASSWORD     - credentials (required)
  TARGET_HOURS        - hours to accumulate (default: 35)
  PARALLEL_SESSIONS   - number of parallel browser sessions (default: 5)
  HEARTBEAT_INTERVAL  - seconds between heartbeats (default: 3, normal is 60)
  HEADLESS            - run headless (default: 1)
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
from playwright.async_api import async_playwright, Playwright

env_file = sys.argv[1] if len(sys.argv) > 1 else ".env"
load_dotenv(env_file, override=True)

EMAIL = os.environ.get("EMAIL", "")
PASSWORD = os.environ.get("PASSWORD", "")
TARGET_HOURS = float(os.environ.get("TARGET_HOURS", "35"))
PARALLEL_SESSIONS = int(os.environ.get("PARALLEL_SESSIONS", "5"))
FAST_HEARTBEAT_SEC = int(os.environ.get("HEARTBEAT_INTERVAL", "3"))
HEADLESS = os.environ.get("HEADLESS", "1") == "1"

NORMAL_HEARTBEAT_INTERVAL = 60

# Health check every 60s, status report every 5 min
HEALTH_CHECK_INTERVAL = 60
STATUS_REPORT_INTERVAL = 300


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


async def login_and_setup(browser, session_id: int) -> dict | None:
    """
    Create a browser context, login, navigate to Stories, enter a story.
    Returns session info dict or None on failure.
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

    # Intercept session/start to lower heartbeat interval
    async def route_handler(route):
        response = await route.fetch()
        try:
            body = await response.json()
            if (
                "result" in body
                and body["result"]
                and "heartbeat_interval_seconds" in body["result"]
            ):
                original = body["result"]["heartbeat_interval_seconds"]
                body["result"]["heartbeat_interval_seconds"] = FAST_HEARTBEAT_SEC
                log(
                    f"{tag} Intercepted heartbeat interval: "
                    f"{original}s -> {FAST_HEARTBEAT_SEC}s"
                )
            await route.fulfill(
                response=response,
                body=json.dumps(body),
                headers={
                    **response.headers,
                    "content-type": "application/json",
                },
            )
        except Exception:
            await route.fulfill(response=response)

    await page.route("**/api/v3/session/start", route_handler)

    try:
        # Login
        log(f"{tag} Logging in...")
        await page.goto(
            "https://login.rosettastone.com/login",
            wait_until="networkidle",
            timeout=60000,
        )
        await asyncio.sleep(2)

        # Accept cookies
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

        # Handle ULEAM
        try:
            content = await page.content()
            if "uleam" in content.lower():
                log(f"{tag} Selecting institutional account...")
                el = page.get_by_text("uleam", exact=False).first
                if await el.is_visible(timeout=5000):
                    await el.click()
                    await asyncio.sleep(3)
                    try:
                        await page.wait_for_load_state(
                            "networkidle", timeout=10000
                        )
                    except Exception:
                        pass
                    pw2 = await fill(["input[type='password']"], PASSWORD)
                    if pw2:
                        await asyncio.sleep(1)
                        await pw2.press("Enter")
                    await asyncio.sleep(5)
                    try:
                        await page.wait_for_load_state(
                            "networkidle", timeout=20000
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        # Navigate to Foundations
        log(f"{tag} Authenticating with totale...")
        try:
            el = page.get_by_text("Foundations", exact=False).first
            if not await el.is_visible(timeout=3000):
                el = page.get_by_text("Fundamentos", exact=False).first
            await el.click()
            await asyncio.sleep(8)
            try:
                await page.wait_for_load_state(
                    "networkidle", timeout=20000
                )
            except Exception:
                pass
        except Exception:
            pass

        # Navigate to Stories
        log(f"{tag} Navigating to Stories...")
        await page.goto(
            "https://totale.rosettastone.com/stories",
            wait_until="networkidle",
            timeout=60000,
        )
        await asyncio.sleep(5)

        # Dismiss audio modal
        try:
            btn = page.locator(
                "button:has-text('Continuar'), button:has-text('Continue')"
            ).first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await asyncio.sleep(2)
        except Exception:
            pass

        # Enter a story
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

        # Dismiss story modals
        for btn_text in ["Continuar", "Continue", "Escuchar", "Listen"]:
            try:
                btn = page.locator(f"button:has-text('{btn_text}')").first
                if await btn.is_visible(timeout=1500):
                    await btn.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

        log(f"{tag} Session ready. JS heartbeats every {FAST_HEARTBEAT_SEC}s.")

        return {
            "session_id": session_id,
            "context": context,
            "page": page,
            "story": story_name,
            "alive": True,
        }

    except Exception as e:
        log(f"{tag} Setup failed: {e}")
        try:
            await context.close()
        except Exception:
            pass
        return None


async def is_page_alive(page) -> bool:
    """Check if a page's browser connection is still alive."""
    try:
        await page.evaluate("1+1")
        return True
    except Exception:
        return False


async def setup_all_sessions(
    pw: Playwright,
) -> tuple:
    """Launch browser and setup all sessions. Returns (browser, sessions)."""
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
        session = await login_and_setup(browser, i + 1)
        if session:
            sessions.append(session)
        else:
            log(f"Session {i + 1} failed to setup, continuing with others...")
        if i < PARALLEL_SESSIONS - 1:
            await asyncio.sleep(3)

    return browser, sessions


async def recover_session(browser, session: dict) -> dict | None:
    """Try to recover a single dead session by creating a new context."""
    sid = session["session_id"]
    tag = f"[S{sid}]"
    log(f"{tag} Recovering session...")

    # Close old context if possible
    try:
        await session["context"].close()
    except Exception:
        pass

    # Create fresh session
    new_session = await login_and_setup(browser, sid)
    if new_session:
        log(f"{tag} Recovery successful!")
    else:
        log(f"{tag} Recovery failed.")
    return new_session


async def main():
    if not EMAIL or not PASSWORD:
        print("ERROR: Set EMAIL and PASSWORD in .env")
        return

    print("=" * 60)
    print("Rosetta Stone - Fast Stories V3")
    print("=" * 60)
    print(f"  Email:            {EMAIL}")
    print(f"  Target:           {TARGET_HOURS}h")
    print(f"  Parallel sessions: {PARALLEL_SESSIONS}")
    print(f"  Heartbeat interval: {FAST_HEARTBEAT_SEC}s (normal: {NORMAL_HEARTBEAT_INTERVAL}s)")
    print(f"  Headless:         {HEADLESS}")
    print()
    speedup_hb = NORMAL_HEARTBEAT_INTERVAL / FAST_HEARTBEAT_SEC
    print(f"  Potential speedup: {PARALLEL_SESSIONS} sessions x {speedup_hb:.0f}x heartbeat = {PARALLEL_SESSIONS * speedup_hb:.0f}x")
    total_speedup = PARALLEL_SESSIONS * speedup_hb
    print(f"  Best case:  {TARGET_HOURS}h in ~{TARGET_HOURS / total_speedup:.1f}h ({total_speedup:.0f}x speedup)")
    print(f"  Worst case: {TARGET_HOURS}h in ~{TARGET_HOURS / PARALLEL_SESSIONS:.1f}h (1x per session)")
    print("=" * 60)
    print()

    start_time = time.time()
    total_session_seconds = 0.0  # accumulated across restarts
    restart_count = 0

    async with async_playwright() as pw:
        browser = None
        sessions = []

        try:
            while True:
                # Setup browser + sessions if needed
                if not sessions:
                    if browser:
                        try:
                            await browser.close()
                        except Exception:
                            pass

                    if restart_count > 0:
                        log(f"Restarting browser (restart #{restart_count})...")
                        await asyncio.sleep(5)

                    browser, sessions = await setup_all_sessions(pw)
                    restart_count += 1

                    if not sessions:
                        log("ERROR: No sessions established. Retrying in 30s...")
                        await asyncio.sleep(30)
                        continue

                    log(f"\n{len(sessions)}/{PARALLEL_SESSIONS} sessions active.")

                    wall_hours_needed = TARGET_HOURS / len(sessions)
                    log(f"Running for ~{wall_hours_needed:.1f}h wall time ({len(sessions)} parallel sessions)")
                    log("Press Ctrl+C to stop early.\n")

                # Health check + monitoring loop
                last_report_time = time.time()
                segment_start = time.time()

                while sessions:
                    await asyncio.sleep(HEALTH_CHECK_INTERVAL)

                    # Check which sessions are alive
                    browser_alive = False
                    dead_indices = []

                    for i, session in enumerate(sessions):
                        alive = await is_page_alive(session["page"])
                        session["alive"] = alive
                        if alive:
                            browser_alive = True
                        else:
                            dead_indices.append(i)

                    active_count = len(sessions) - len(dead_indices)

                    # If browser itself died (all pages dead), break for full restart
                    if not browser_alive:
                        segment_elapsed = time.time() - segment_start
                        total_session_seconds += segment_elapsed * len(sessions)
                        log("Browser process died. All pages disconnected.")
                        sessions = []
                        break

                    # Try to recover individual dead sessions
                    for i in reversed(dead_indices):
                        old_session = sessions[i]
                        new_session = await recover_session(browser, old_session)
                        if new_session:
                            sessions[i] = new_session
                        else:
                            # Remove permanently dead session
                            sessions.pop(i)

                    # Status report every STATUS_REPORT_INTERVAL
                    now = time.time()
                    if now - last_report_time >= STATUS_REPORT_INTERVAL:
                        last_report_time = now

                        elapsed_h = (now - start_time) / 3600
                        segment_h = (now - segment_start) / 3600
                        current_segment_credit = segment_h * len(sessions)
                        total_credit_h = (
                            total_session_seconds / 3600 + current_segment_credit
                        )

                        active = sum(
                            1 for s in sessions if s.get("alive", False)
                        )
                        log(
                            f"Running {elapsed_h:.2f}h | "
                            f"{active}/{len(sessions)} active | "
                            f"Credit: ~{total_credit_h:.1f}h | "
                            f"Restarts: {restart_count - 1}"
                        )

                        # Check if target reached
                        if total_credit_h >= TARGET_HOURS:
                            log(
                                f"Target {TARGET_HOURS}h reached "
                                f"(~{total_credit_h:.1f}h credited). Stopping."
                            )
                            segment_elapsed = now - segment_start
                            total_session_seconds += (
                                segment_elapsed * len(sessions)
                            )
                            sessions = []
                            break

                    # If no sessions left after recovery, trigger full restart
                    if not sessions:
                        break

                # If sessions were cleared for target reached, stop
                elapsed_h = (time.time() - start_time) / 3600
                total_credit_h = total_session_seconds / 3600
                if total_credit_h >= TARGET_HOURS:
                    break

        except KeyboardInterrupt:
            elapsed = time.time() - start_time
            log(f"\nStopped after {elapsed / 3600:.2f}h")

        # Final summary
        elapsed = time.time() - start_time
        total_credit_h = total_session_seconds / 3600

        print("\n" + "=" * 60)
        print("SESSION SUMMARY")
        print("=" * 60)
        print(f"  Wall time:          {elapsed / 3600:.2f}h")
        print(f"  Browser restarts:   {restart_count - 1}")
        print(f"  Credit estimate:    ~{total_credit_h:.1f}h")
        print("=" * 60)

        if browser:
            try:
                await browser.close()
            except Exception:
                pass

    log("Done. Ask the institution admin to check Stories hours.")


if __name__ == "__main__":
    asyncio.run(main())
