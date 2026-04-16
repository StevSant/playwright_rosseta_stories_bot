"""
Fast Rosetta Stone Stories hour accumulation - V2.

Based on reverse-engineering StoriesModule.js, the correct flow is:

  1. report_usage(started_ago=0, usage_length=0, language, session_id)
     → Initializes a tracking session (called once when entering a story)

  2. report_additional_usage(usage_length=delta_seconds, session_id)
     → Adds incremental time to the session (called on each mode change)

The original fast_stories.py called report_usage with large usage_length,
but the real JS player NEVER does that. It always initializes with 0 and
accumulates via report_additional_usage.

This script:
  1. Logs in and navigates to Stories
  2. Enters a story (so StoriesModule initializes properly)
  3. Intercepts the report_usage call to capture the session_id
  4. Sends report_additional_usage calls with the desired time increments
  5. Keeps the browser open (session stays valid)

Usage:
  uv run python fast_stories_v2.py              # uses .env
  uv run python fast_stories_v2.py .env_daniela # specific env file
"""

import asyncio
import json
import os
import sys
import time
import uuid
import urllib.error
import urllib.request
from datetime import datetime

from dotenv import load_dotenv
from playwright.async_api import async_playwright

env_file = sys.argv[1] if len(sys.argv) > 1 else ".env"
load_dotenv(env_file, override=True)

EMAIL = os.environ.get("EMAIL", "")
PASSWORD = os.environ.get("PASSWORD", "")
TARGET_HOURS = float(os.environ.get("TARGET_HOURS", "35"))
HEADLESS = os.environ.get("HEADLESS", "1") == "1"

LCP_BASE = "https://lcp.rosettastone.com"
DASHBOARD_BASE = "https://prism.rosettastone.com/reports/learner/dashboard"


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
        body_text = e.read().decode()[:300]
        log(f"HTTP {e.code}: {body_text}")
        return None
    except Exception as e:
        log(f"HTTP error: {e}")
        return None


def get_dashboard(access_token: str, user_guid: str) -> dict | None:
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
            mobile = data.get("allTimeActivities", {}).get("mobileTimeSpentMs", 0)
            return {
                "name": data.get("name", "Unknown"),
                "total_h": total / 3600000,
                "elearn_h": elearn / 3600000,
                "mobile_h": mobile / 3600000,
            }
    except Exception as e:
        log(f"Dashboard error: {e}")
        return None


def report_usage_init(cookies: str, language: str, session_id: str) -> dict | None:
    """Initialize a stories usage session (mirroring what StoriesModule does first)."""
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
    """Report additional usage time (mirroring StoriesModule's incremental reports)."""
    return http_post(
        f"{LCP_BASE}/api/v3/app_usage/report_additional_usage",
        {
            "usage_length": usage_length_sec,
            "session_identifier": session_id,
        },
        cookies,
    )


async def main():
    if not EMAIL or not PASSWORD:
        print("ERROR: Set EMAIL and PASSWORD in .env")
        return

    print("=" * 60)
    print("Rosetta Stone - Fast Stories V2")
    print("=" * 60)
    print(f"  Email:   {EMAIL}")
    print(f"  Target:  {TARGET_HOURS}h")
    print(f"  Method:  report_additional_usage (correct API flow)")
    print("=" * 60)
    print()

    access_token = ""
    user_guid = ""
    captured_session_id = ""
    captured_report_usage = False

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"],
        )
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

        # Capture auth tokens and report_usage calls
        async def on_resp(response):
            nonlocal access_token, user_guid, captured_session_id, captured_report_usage
            url = response.url

            if "authentication/login" in url:
                try:
                    body = await response.json()
                    if "auth_data" in body:
                        access_token = body["auth_data"].get("access_token", "")
                        user_guid = body["auth_data"].get("userId", "")
                except Exception:
                    pass

            # Capture the JS player's initial report_usage call
            if "app_usage/report_usage" in url and not captured_report_usage:
                captured_report_usage = True
                log("Captured JS player's report_usage call!")

        async def on_request(request):
            nonlocal captured_session_id
            if "app_usage/report_usage" in request.url and not captured_session_id:
                try:
                    data = json.loads(request.post_data)
                    captured_session_id = data.get("session_identifier", "")
                    log(f"Captured session_id: {captured_session_id}")
                except Exception:
                    pass

        page.on("response", lambda r: asyncio.ensure_future(on_resp(r)))
        page.on("request", lambda r: asyncio.ensure_future(on_request(r)))

        # ===== Login =====
        log("Logging in...")
        await page.goto(
            "https://login.rosettastone.com/login",
            wait_until="networkidle",
            timeout=60000,
        )
        await asyncio.sleep(3)

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
            ["input[type='email']", "input[autocomplete='email']", "input[name='email']"],
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

        # Navigate to Foundations
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

        # Navigate to Stories
        log("Navigating to Stories...")
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
                await asyncio.sleep(3)
        except Exception:
            pass

        log("On Stories page.")

        # Check dashboard before
        dashboard = get_dashboard(access_token, user_guid)
        if dashboard:
            log(f"User: {dashboard['name']}")
            log(f"Dashboard BEFORE: total={dashboard['total_h']:.4f}h | elearn={dashboard['elearn_h']:.4f}h")

        # ===== Enter a story (triggers StoriesModule initialization) =====
        log("Entering a story to trigger StoriesModule initialization...")
        await asyncio.sleep(3)

        story_clicked = False
        # Stories are React cards rendered by StoriesModule
        # Click by known story titles (from the actual stories page)
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
        for name in known_stories:
            try:
                el = page.get_by_text(name, exact=True).first
                if await el.is_visible(timeout=1000):
                    await el.click()
                    story_clicked = True
                    log(f"Clicked story: {name}")
                    break
            except Exception:
                continue

        if story_clicked:
            await asyncio.sleep(8)

            # Dismiss any modals
            for btn_text in ["Continuar", "Continue", "Escuchar", "Listen"]:
                try:
                    btn = page.locator(f"button:has-text('{btn_text}')").first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await asyncio.sleep(2)
                except Exception:
                    pass

            # Wait for StoriesModule to make its report_usage call
            log("Waiting for StoriesModule to initialize tracking...")
            for _ in range(15):
                if captured_session_id:
                    break
                await asyncio.sleep(2)

        # Capture cookies
        cookies = await context.cookies()
        relevant = [c for c in cookies if "rosettastone.com" in c.get("domain", "")]
        cookies_str = "; ".join(f"{c['name']}={c['value']}" for c in relevant)

        if not captured_session_id:
            log("StoriesModule didn't fire report_usage. Creating our own session...")
            captured_session_id = str(uuid.uuid4())

            # Initialize the session ourselves, following the exact JS pattern
            log(f"Initializing with report_usage(0, 0, ENG, {captured_session_id[:8]}...)")
            result = report_usage_init(cookies_str, "ENG", captured_session_id)
            if result is None:
                log("report_usage initialization FAILED. Exiting.")
                await browser.close()
                return
            log(f"report_usage init response: {result}")
        else:
            log(f"Using JS-captured session_id: {captured_session_id[:8]}...")

        # ===== Send report_additional_usage with target hours =====
        log(f"\nReporting {TARGET_HOURS}h via report_additional_usage...")
        log("(Using incremental reports matching StoriesModule pattern)")

        total_seconds = int(TARGET_HOURS * 3600)
        # Send in chunks mimicking play mode transitions (5-15 minute chunks)
        chunk_min = 5 * 60   # 5 minutes
        chunk_max = 15 * 60  # 15 minutes
        seconds_reported = 0
        chunk_count = 0

        import random

        while seconds_reported < total_seconds:
            remaining = total_seconds - seconds_reported
            chunk = min(remaining, random.randint(chunk_min, chunk_max))

            result = report_additional_usage(cookies_str, chunk, captured_session_id)

            if result is None:
                log(f"report_additional_usage FAILED at {seconds_reported}s. Stopping.")
                break

            seconds_reported += chunk
            chunk_count += 1

            if chunk_count % 10 == 0:
                hours_done = seconds_reported / 3600
                log(f"  {chunk_count} chunks | {hours_done:.1f}h reported so far...")

            # Small delay between calls to avoid rate limiting
            await asyncio.sleep(0.5)

        hours_reported = seconds_reported / 3600
        log(f"Reported {chunk_count} chunks totaling {hours_reported:.2f}h")

        # Wait for server to process
        await asyncio.sleep(5)

        # Check dashboard after
        dashboard_after = get_dashboard(access_token, user_guid)
        if dashboard_after:
            log(f"Dashboard AFTER: total={dashboard_after['total_h']:.4f}h | elearn={dashboard_after['elearn_h']:.4f}h")
            if dashboard:
                diff = dashboard_after['total_h'] - dashboard['total_h']
                log(f"Dashboard change: {diff:+.4f}h")
                if diff < 0.01:
                    log("(Note: Stories time may be in a separate admin-only bucket)")

        log("\nDone! Ask the institution admin to check Stories hours.")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
