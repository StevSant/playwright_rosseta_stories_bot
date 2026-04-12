"""
Fast Rosetta Stone Stories hour accumulation.

Uses the same report_usage API that the Stories JavaScript player uses,
but submits hours in bulk instead of tracking real-time playback.

How it works:
  1. Login with Playwright (~30s) → navigate to Stories to get session cookies
  2. Close browser
  3. Send report_usage calls via HTTP with usage_length set to target hours
  4. Optionally keep heartbeats running as backup

Endpoints (from StoriesModule.js):
  POST lcp.rosettastone.com/api/v3/app_usage/report_usage
    {app_identifier: "stories", started_ago, usage_length, language, session_identifier}
  POST lcp.rosettastone.com/api/v3/app_usage/report_additional_usage
    {usage_length, session_identifier}

Usage:
  uv run python fast_stories.py                     # uses default .env
  uv run python fast_stories.py .env_daniela        # uses specific env file

Environment variables (in .env file or shell):
  EMAIL          - Rosetta Stone email (required)
  PASSWORD       - Rosetta Stone password (required)
  TARGET_HOURS   - Hours to accumulate (default: 35)
  HEADLESS       - Run browser headless during login (default: 1)
  MODE           - "report" for instant report_usage, "heartbeat" for real-time,
                   "both" for both approaches (default: both)
"""

import asyncio
import json
import os
import random
import signal
import sys
import time
import uuid
import urllib.error
import urllib.request
from datetime import datetime

from dotenv import load_dotenv
from playwright.async_api import async_playwright

# --- Load .env file ---
# Pass a specific env file as first argument, or defaults to .env
env_file = sys.argv[1] if len(sys.argv) > 1 else ".env"
load_dotenv(env_file, override=True)

# --- Configuration ---
EMAIL = os.environ.get("EMAIL", "")
PASSWORD = os.environ.get("PASSWORD", "")
TARGET_HOURS = float(os.environ.get("TARGET_HOURS", "35"))
HEADLESS = os.environ.get("HEADLESS", "1") == "1"
MODE = os.environ.get("MODE", "both")  # "report", "heartbeat", or "both"

LOGIN_URL = "https://login.rosettastone.com/login"
LCP_BASE = "https://lcp.rosettastone.com"
DASHBOARD_BASE = "https://prism.rosettastone.com/reports/learner/dashboard"

HEARTBEAT_INTERVAL_SEC = 30
SESSION_REFRESH_HOURS = 6


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def http_post(url: str, body: dict, cookies: str) -> dict | None:
    """Send a POST request with cookies, return parsed JSON or None."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Cookie": cookies,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://totale.rosettastone.com/",
            "Origin": "https://totale.rosettastone.com",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        log(f"HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        log(f"HTTP error: {e}")
        return None


def get_dashboard(access_token: str, user_guid: str) -> dict | None:
    """Get hours from dashboard API."""
    req = urllib.request.Request(
        f"{DASHBOARD_BASE}/{user_guid}?skipLastUsageDate=true",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            total = data.get("allTimeActivities", {}).get("totalTimeSpentMs", 0)
            elearn = data.get("allTimeActivities", {}).get("elearningTimeSpentMs", 0)
            mobile = data.get("allTimeActivities", {}).get("mobileTimeSpentMs", 0)
            return {
                "name": data.get("name", "Unknown"),
                "total_h": total / 3600000,
                "elearn_h": elearn / 3600000,
                "mobile_h": mobile / 3600000,
            }
    except Exception:
        return None


async def login_and_get_cookies(email: str, password: str, headless: bool) -> tuple[str, str, str]:
    """Login, navigate to Stories, return (cookies_str, access_token, user_guid)."""
    access_token = ""
    user_guid = ""

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="es-ES",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        async def on_resp(response):
            nonlocal access_token, user_guid
            if "authentication/login" in response.url:
                try:
                    body = await response.json()
                    if "auth_data" in body:
                        access_token = body["auth_data"].get("access_token", "")
                        user_guid = body["auth_data"].get("userId", "")
                except Exception:
                    pass

        page.on("response", lambda r: asyncio.ensure_future(on_resp(r)))

        # Login
        log("Logging in...")
        await page.goto(LOGIN_URL, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)

        try:
            btn = page.locator("button:has-text('Accept'), button:has-text('Aceptar')").first
            if await btn.is_visible(timeout=2000):
                await btn.click()
        except Exception:
            pass

        async def fill(sels, val):
            for sel in sels:
                try:
                    f = page.locator(sel).first
                    if await f.is_visible(timeout=2000):
                        await f.fill(val)
                        return f
                except Exception:
                    continue
            for frame in page.frames:
                for sel in sels:
                    try:
                        f = frame.locator(sel).first
                        if await f.is_visible(timeout=2000):
                            await f.fill(val)
                            return f
                    except Exception:
                        continue
            return None

        await fill(["input[type='email']", "input[autocomplete='email']", "input[name='email']"], email)
        pw = await fill(["input[type='password']", "input[name='password']"], password)
        if pw:
            await asyncio.sleep(1)
            await pw.press("Enter")

        await asyncio.sleep(5)
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass

        # Handle ULEAM institutional account
        try:
            content = await page.content()
            if "uleam" in content.lower():
                log("Selecting institutional account...")
                el = page.get_by_text("uleam", exact=False).first
                if await el.is_visible(timeout=5000):
                    await el.click()
                    await asyncio.sleep(3)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    pw2 = await fill(["input[type='password']"], password)
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

        # Navigate to Foundations → totale auth
        log("Authenticating with totale...")
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

        # Navigate to Stories (establishes LCP session)
        log("Navigating to Stories...")
        await page.goto("https://totale.rosettastone.com/stories", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5)

        # Dismiss audio modal
        try:
            btn = page.locator("button:has-text('Continuar'), button:has-text('Continue')").first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await asyncio.sleep(3)
        except Exception:
            pass

        await asyncio.sleep(5)

        # Capture cookies
        cookies = await context.cookies()
        relevant = [c for c in cookies if "rosettastone.com" in c.get("domain", "")]
        cookies_str = "; ".join(f"{c['name']}={c['value']}" for c in relevant)

        rack = [c for c in cookies if c["name"] == "rack.session"]
        if not rack:
            log("WARNING: rack.session cookie not found!")

        await browser.close()

    return cookies_str, access_token, user_guid


def report_stories_usage(cookies: str, hours: float, language: str = "ENG") -> bool:
    """
    Report stories usage time via the same API the JavaScript player uses.
    Splits into multiple sessions for realism.
    """
    total_seconds = int(hours * 3600)
    # Split into sessions of 30-60 minutes for realism
    session_length_range = (30 * 60, 60 * 60)  # 30-60 min
    seconds_reported = 0
    session_count = 0

    while seconds_reported < total_seconds:
        remaining = total_seconds - seconds_reported
        session_length = min(remaining, random.randint(*session_length_range))
        session_id = str(uuid.uuid4())
        started_ago = total_seconds - seconds_reported + random.randint(60, 300)

        # report_usage (initial session report)
        result = http_post(
            f"{LCP_BASE}/api/v3/app_usage/report_usage",
            {
                "app_identifier": "stories",
                "app_version": "11.11.2",
                "started_ago": started_ago,
                "usage_length": session_length,
                "language": language,
                "session_identifier": session_id,
            },
            cookies,
        )

        if result is None:
            log(f"report_usage failed at {seconds_reported}s")
            return False

        seconds_reported += session_length
        session_count += 1

        if session_count % 10 == 0:
            log(f"  Reported {session_count} sessions, {seconds_reported/3600:.1f}h so far...")

    log(f"  Reported {session_count} sessions totaling {seconds_reported/3600:.2f}h")
    return True


def send_heartbeat(cookies: str) -> bool:
    """Send a single heartbeat."""
    req = urllib.request.Request(
        f"{LCP_BASE}/api/v3/session/heartbeat",
        data=b"",
        headers={
            "Content-Type": "application/json",
            "Cookie": cookies,
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://totale.rosettastone.com/",
            "Origin": "https://totale.rosettastone.com",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


async def main():
    email = EMAIL
    password = PASSWORD

    if not email or not password:
        print("ERROR: Set EMAIL and PASSWORD environment variables")
        print()
        print("Usage:")
        print("  EMAIL=user@email.com PASSWORD=pass TARGET_HOURS=35 uv run python fast_stories.py")
        print()
        print("Modes (set via MODE env var):")
        print("  report    - Send report_usage API calls (instant, recommended)")
        print("  heartbeat - Keep session alive with heartbeats (real-time)")
        print("  both      - Do both (default)")
        return

    print("=" * 60)
    print("Rosetta Stone - Fast Stories Completion")
    print("=" * 60)
    print(f"  Email:   {email}")
    print(f"  Target:  {TARGET_HOURS}h")
    print(f"  Mode:    {MODE}")
    print("=" * 60)
    print()

    signal.signal(signal.SIGINT, lambda *_: (print("\nStopped."), sys.exit(0)))

    # Step 1: Login and get cookies
    cookies, token, guid = await login_and_get_cookies(email, password, HEADLESS)
    if not cookies:
        log("Failed to get session cookies. Exiting.")
        return

    log("Session established, browser closed.")

    # Step 2: Check current dashboard hours
    dashboard = get_dashboard(token, guid)
    if dashboard:
        log(f"User: {dashboard['name']}")
        log(f"Dashboard: total={dashboard['total_h']:.2f}h | elearning={dashboard['elearn_h']:.2f}h | mobile={dashboard['mobile_h']:.2f}h")
        log(f"(Note: Stories time may not appear in student dashboard - institution admin sees it)")

    # Step 3: Report stories usage (instant)
    if MODE in ("report", "both"):
        log(f"\nReporting {TARGET_HOURS}h of Stories usage via API...")
        ok = report_stories_usage(cookies, TARGET_HOURS)
        if ok:
            log(f"Successfully reported {TARGET_HOURS}h of Stories time!")
        else:
            log("report_usage failed. Falling back to heartbeat mode.")

    # Step 4: Heartbeat mode (real-time backup)
    if MODE in ("heartbeat", "both"):
        log(f"\nStarting heartbeat mode (keeps session alive)...")
        log(f"Heartbeat every {HEARTBEAT_INTERVAL_SEC}s. Ctrl+C to stop.")
        log("(This accumulates real-time session hours as backup)\n")

        hb_count = 0
        failures = 0
        start = time.time()

        while True:
            ok = send_heartbeat(cookies)
            if ok:
                hb_count += 1
                failures = 0
            else:
                failures += 1
                if failures >= 5:
                    log("Too many heartbeat failures. Re-authenticating...")
                    cookies, token, guid = await login_and_get_cookies(email, password, HEADLESS)
                    if not cookies:
                        log("Re-auth failed. Exiting.")
                        return
                    failures = 0
                    log("Session refreshed.")

            if hb_count % 120 == 0 and hb_count > 0:
                elapsed_h = (time.time() - start) / 3600
                log(f"Heartbeats: {hb_count} | Running for {elapsed_h:.2f}h")

            await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)

    log("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
