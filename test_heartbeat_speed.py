"""
Test whether sending heartbeats faster than normal accumulates time faster.

Plan:
  1. Login, navigate to Stories (establish real session)
  2. Check dashboard time BEFORE
  3. Send heartbeats at accelerated rate (every 2s instead of 30s) for 2 minutes
     That's ~60 heartbeats in 2 min. At normal rate (30s each), 60 beats = 30 min of credit.
     If fast heartbeats work, dashboard should show ~30 min increase in only 2 min.
  4. Check dashboard time AFTER
  5. Compare the difference
"""

import asyncio
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

from dotenv import load_dotenv
from playwright.async_api import async_playwright

env_file = sys.argv[1] if len(sys.argv) > 1 else ".env"
load_dotenv(env_file, override=True)

EMAIL = os.environ.get("EMAIL", "")
PASSWORD = os.environ.get("PASSWORD", "")

LCP_BASE = "https://lcp.rosettastone.com"
DASHBOARD_BASE = "https://prism.rosettastone.com/reports/learner/dashboard"

# Test parameters
HEARTBEAT_INTERVAL = 2       # seconds between heartbeats (normal is 30)
TEST_DURATION = 120           # total seconds to run the test
EXPECTED_CREDIT_PER_BEAT = 30 # seconds the server might credit per beat


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


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
            return {
                "total_ms": data.get("allTimeActivities", {}).get("totalTimeSpentMs", 0),
                "elearn_ms": data.get("allTimeActivities", {}).get("elearningTimeSpentMs", 0),
                "mobile_ms": data.get("allTimeActivities", {}).get("mobileTimeSpentMs", 0),
            }
    except Exception as e:
        log(f"Dashboard error: {e}")
        return None


def send_heartbeat(cookies: str) -> bool:
    req = urllib.request.Request(
        f"{LCP_BASE}/api/v3/session/heartbeat",
        data=b"",
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
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        log(f"Heartbeat error: {e}")
        return False


async def main():
    if not EMAIL or not PASSWORD:
        print("ERROR: Set EMAIL and PASSWORD in .env")
        return

    print("=" * 60)
    print("HEARTBEAT SPEED TEST")
    print("=" * 60)
    print(f"  Heartbeat interval: {HEARTBEAT_INTERVAL}s (normal: 30s)")
    print(f"  Test duration: {TEST_DURATION}s")
    print(f"  Expected beats: ~{TEST_DURATION // HEARTBEAT_INTERVAL}")
    print(f"  If fast beats work: ~{(TEST_DURATION // HEARTBEAT_INTERVAL) * EXPECTED_CREDIT_PER_BEAT / 60:.0f} min credited")
    print(f"  If only real-time: ~{TEST_DURATION / 60:.0f} min credited")
    print("=" * 60)
    print()

    access_token = ""
    user_guid = ""

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
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
        await page.goto("https://login.rosettastone.com/login", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)

        try:
            btn = page.locator("button:has-text('Accept'), button:has-text('Aceptar')").first
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

        await fill(["input[type='email']", "input[autocomplete='email']", "input[name='email']"], EMAIL)
        pw_field = await fill(["input[type='password']", "input[name='password']"], PASSWORD)
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

        await asyncio.sleep(3)

        # Capture cookies for HTTP heartbeats
        cookies = await context.cookies()
        relevant = [c for c in cookies if "rosettastone.com" in c.get("domain", "")]
        cookies_str = "; ".join(f"{c['name']}={c['value']}" for c in relevant)

        rack = [c for c in cookies if c["name"] == "rack.session"]
        if not rack:
            log("WARNING: No rack.session cookie found!")
        else:
            log("rack.session cookie captured.")

        log("Session established on Stories page.")

        # Step 1: Check dashboard BEFORE
        log("Checking dashboard BEFORE test...")
        before = get_dashboard(access_token, user_guid)
        if before:
            log(f"  BEFORE: total={before['total_ms']/3600000:.4f}h | elearn={before['elearn_ms']/3600000:.4f}h")
        else:
            log("  Could not read dashboard before test.")

        # Step 2: Send rapid heartbeats (while browser stays open on Stories)
        log(f"\nSending rapid heartbeats every {HEARTBEAT_INTERVAL}s for {TEST_DURATION}s...")
        log("(Browser stays open on Stories page - JS also sends its own heartbeats)")

        beat_count = 0
        failures = 0
        start_time = time.time()

        while time.time() - start_time < TEST_DURATION:
            ok = send_heartbeat(cookies_str)
            beat_count += 1
            if ok:
                failures = 0
            else:
                failures += 1
                if failures >= 5:
                    log("Too many failures, stopping.")
                    break

            elapsed = time.time() - start_time
            if beat_count % 10 == 0:
                log(f"  {beat_count} beats sent | {elapsed:.0f}s elapsed")

            await asyncio.sleep(HEARTBEAT_INTERVAL)

        elapsed_total = time.time() - start_time
        log(f"\nDone: {beat_count} heartbeats in {elapsed_total:.0f}s")

        # Step 3: Wait a moment for server to process
        log("Waiting 10s for server to process...")
        await asyncio.sleep(10)

        # Step 4: Check dashboard AFTER
        log("Checking dashboard AFTER test...")
        after = get_dashboard(access_token, user_guid)
        if after:
            log(f"  AFTER:  total={after['total_ms']/3600000:.4f}h | elearn={after['elearn_ms']/3600000:.4f}h")
        else:
            log("  Could not read dashboard after test.")

        # Step 5: Calculate results
        if before and after:
            diff_total_ms = after["total_ms"] - before["total_ms"]
            diff_elearn_ms = after["elearn_ms"] - before["elearn_ms"]
            diff_total_min = diff_total_ms / 60000
            diff_elearn_min = diff_elearn_ms / 60000

            print("\n" + "=" * 60)
            print("RESULTS")
            print("=" * 60)
            print(f"  Wall time elapsed:    {elapsed_total / 60:.1f} min")
            print(f"  Heartbeats sent:      {beat_count}")
            print(f"  Total time gained:    {diff_total_min:.2f} min")
            print(f"  E-learning gained:    {diff_elearn_min:.2f} min")
            print()

            if diff_total_min > 0:
                speedup = diff_total_min / (elapsed_total / 60)
                print(f"  SPEEDUP FACTOR:       {speedup:.1f}x")
                if speedup > 2:
                    print(f"  FAST HEARTBEATS WORK!")
                    est_hours_per_hour = speedup
                    print(f"  Estimated: {est_hours_per_hour:.0f}h credit per 1h wall time")
                    print(f"  35h would take ~{35 / est_hours_per_hour:.1f}h")
                else:
                    print(f"  Server credits real-time only (1x speed).")
                    print(f"  Fast heartbeats don't help.")
            else:
                print("  NO TIME GAINED - heartbeats may not count here")
                print("  (Stories time might be in a separate bucket not shown on dashboard)")
            print("=" * 60)
        else:
            log("Could not compare - dashboard read failed.")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
