"""
Probe: confirm whether entering a Story and idling triggers
`app_usage/report_additional_usage` automatically (via the JS heartbeat),
OR only on user interaction (mode change).

Uses the v3 heartbeat interception to force fast heartbeats and see if
that cascades into faster usage reporting. Logs every lcp.rosettastone.com
call and prints a summary.
"""

import asyncio
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime

from dotenv import load_dotenv
from playwright.async_api import async_playwright

env_file = sys.argv[1] if len(sys.argv) > 1 else ".env_otro"
load_dotenv(env_file, override=True)

EMAIL = os.environ.get("EMAIL", "")
PASSWORD = os.environ.get("PASSWORD", "")
FAST_HEARTBEAT = 3
IDLE_DURATION = 90  # seconds to idle in the story while logging

calls: list[dict] = []


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


async def main():
    if not EMAIL or not PASSWORD:
        print("ERROR: Set EMAIL and PASSWORD")
        return

    log(f"Using env: {env_file}  email={EMAIL}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
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

        async def route_handler(route):
            response = await route.fetch()
            try:
                body = await response.json()
                if (
                    "result" in body
                    and body["result"]
                    and "heartbeat_interval_seconds" in body["result"]
                ):
                    orig = body["result"]["heartbeat_interval_seconds"]
                    body["result"]["heartbeat_interval_seconds"] = FAST_HEARTBEAT
                    log(f"Intercepted heartbeat_interval: {orig}s -> {FAST_HEARTBEAT}s")
                await route.fulfill(
                    response=response,
                    body=json.dumps(body),
                    headers={**response.headers, "content-type": "application/json"},
                )
            except Exception:
                await route.fulfill(response=response)

        await page.route("**/api/v3/session/start", route_handler)

        def on_req(request):
            url = request.url
            if "lcp.rosettastone.com" not in url and "prism.rosettastone.com" not in url:
                return
            entry = {
                "ts": time.time(),
                "method": request.method,
                "url": url.split("?")[0],
                "body": None,
            }
            if request.method == "POST":
                try:
                    entry["body"] = request.post_data
                except Exception:
                    pass
            calls.append(entry)

        page.on("request", on_req)

        log("Logging in...")
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
                log("Selecting ULEAM institutional account...")
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

        log("Clicking Foundations/Fundamentos...")
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
        except Exception as e:
            log(f"Foundations click failed: {e}")

        log("Navigating to /stories...")
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

        known = [
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
        story_entered = None
        for name in known:
            try:
                el = page.get_by_text(name, exact=True).first
                if await el.is_visible(timeout=1000):
                    await el.click()
                    story_entered = name
                    break
            except Exception:
                continue

        if not story_entered:
            log("ERROR: no story found")
        else:
            log(f"Entered story: {story_entered}")
            await asyncio.sleep(5)
            for btn_text in ["Continuar", "Continue", "Escuchar", "Listen"]:
                try:
                    btn = page.locator(f"button:has-text('{btn_text}')").first
                    if await btn.is_visible(timeout=1500):
                        await btn.click()
                        await asyncio.sleep(1)
                except Exception:
                    pass

        mark = len(calls)
        log(f"Idling {IDLE_DURATION}s in the story, capturing calls from this point...")
        await asyncio.sleep(IDLE_DURATION)

        new_calls = calls[mark:]
        log(f"Captured {len(new_calls)} calls during idle.")

        counter = Counter()
        for c in new_calls:
            counter[f"{c['method']} {c['url']}"] += 1

        print("\n" + "=" * 60)
        print(f"IDLE-PHASE CALL COUNTS (over {IDLE_DURATION}s, fast_hb={FAST_HEARTBEAT}s)")
        print("=" * 60)
        for endpoint, n in counter.most_common():
            print(f"  {n:4d}x  {endpoint}")
        print("=" * 60)

        interesting = [
            c for c in new_calls
            if any(
                k in c["url"]
                for k in ("heartbeat", "report_usage", "report_additional", "session/start")
            )
        ]
        print("\nSample payloads for time-tracking endpoints:")
        for c in interesting[:15]:
            body_preview = (c["body"] or "")[:200]
            print(f"  - {c['method']} {c['url']}  body={body_preview}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
