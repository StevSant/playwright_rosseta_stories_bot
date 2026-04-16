"""
Capture all network requests during a real Stories session.
Logs every URL, method, payload, and response to identify
which endpoint actually feeds the institution admin dashboard.
"""

import asyncio
import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from playwright.async_api import async_playwright

env_file = sys.argv[1] if len(sys.argv) > 1 else ".env"
load_dotenv(env_file, override=True)

EMAIL = os.environ.get("EMAIL", "")
PASSWORD = os.environ.get("PASSWORD", "")
CAPTURE_DURATION_SEC = int(os.environ.get("CAPTURE_DURATION", "180"))

captured_requests = []


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


async def main():
    if not EMAIL or not PASSWORD:
        print("ERROR: Set EMAIL and PASSWORD in .env")
        return

    log(f"Will capture network traffic for {CAPTURE_DURATION_SEC}s after story starts")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
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

        # --- Network capture handler ---
        async def on_request(request):
            url = request.url
            # Skip static assets, images, fonts, etc.
            skip_extensions = (
                ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
                ".css", ".woff", ".woff2", ".ttf", ".eot",
                ".mp3", ".wav", ".ogg", ".mp4", ".webm",
            )
            if any(url.lower().endswith(ext) for ext in skip_extensions):
                return

            entry = {
                "timestamp": datetime.now().isoformat(),
                "method": request.method,
                "url": url,
                "post_data": None,
            }

            if request.method == "POST":
                try:
                    entry["post_data"] = request.post_data
                except Exception:
                    pass

            captured_requests.append(entry)

        async def on_response(response):
            url = response.url
            # Only capture API-like responses
            if not any(
                keyword in url
                for keyword in (
                    "api/", "report", "usage", "heartbeat", "session",
                    "tracking", "progress", "scorm", "xapi", "lrs",
                    "time", "activity", "analytics", "telemetry",
                    "lcp.", "prism.", "totale.",
                )
            ):
                return

            # Find matching request entry and add response info
            for entry in reversed(captured_requests):
                if entry["url"] == url and "status" not in entry:
                    entry["status"] = response.status
                    try:
                        body = await response.text()
                        # Truncate large responses
                        entry["response_body"] = body[:2000] if len(body) > 2000 else body
                    except Exception:
                        entry["response_body"] = "<could not read>"
                    break

        page.on("request", lambda r: asyncio.ensure_future(on_request(r)))
        page.on("response", lambda r: asyncio.ensure_future(on_response(r)))

        # --- Login flow ---
        log("Logging in...")
        await page.goto(
            "https://login.rosettastone.com/login",
            wait_until="networkidle",
            timeout=60000,
        )
        await asyncio.sleep(3)

        # Accept cookies
        try:
            btn = page.locator("button:has-text('Accept'), button:has-text('Aceptar')").first
            if await btn.is_visible(timeout=2000):
                await btn.click()
        except Exception:
            pass

        # Fill credentials
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
            btn = page.locator("button:has-text('Continuar'), button:has-text('Continue')").first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await asyncio.sleep(3)
        except Exception:
            pass

        log("On Stories page. Clearing captured requests from login phase...")
        login_request_count = len(captured_requests)
        log(f"  ({login_request_count} requests during login - keeping them for reference)")

        # --- Click on the first available story ---
        log("Looking for a story to click...")
        await asyncio.sleep(3)

        story_clicked = False
        # Try clicking any story card/link
        story_selectors = [
            "[data-testid*='story']",
            ".story-card",
            ".story-item",
            "a[href*='story']",
            "[class*='story']",
            "[class*='Story']",
        ]
        for sel in story_selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    await el.click()
                    story_clicked = True
                    log(f"Clicked story element: {sel}")
                    break
            except Exception:
                continue

        if not story_clicked:
            # Try clicking on known story names
            known_stories = [
                "The Shipwreck", "The Surprise", "The Lost City",
                "El naufragio", "La sorpresa", "La ciudad perdida",
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

        if not story_clicked:
            log("Could not find a story to click. Capturing from Stories page instead...")
        else:
            await asyncio.sleep(5)
            # Dismiss any modals after entering story
            try:
                btn = page.locator("button:has-text('Continuar'), button:has-text('Continue')").first
                if await btn.is_visible(timeout=3000):
                    await btn.click()
            except Exception:
                pass

        # --- Capture phase ---
        log(f"=== CAPTURING NETWORK TRAFFIC FOR {CAPTURE_DURATION_SEC}s ===")
        log("(Every API call will be logged)")

        capture_start = len(captured_requests)

        for elapsed in range(0, CAPTURE_DURATION_SEC, 10):
            await asyncio.sleep(10)
            new_count = len(captured_requests) - capture_start
            log(f"  {elapsed + 10}s elapsed | {new_count} new requests captured")

        log("=== CAPTURE COMPLETE ===")

        await browser.close()

    # --- Save results ---
    output_file = "network_capture.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(captured_requests, f, indent=2, ensure_ascii=False)

    log(f"Saved {len(captured_requests)} requests to {output_file}")

    # --- Print summary ---
    print("\n" + "=" * 70)
    print("NETWORK CAPTURE SUMMARY")
    print("=" * 70)

    # Group by domain + path
    from collections import Counter
    url_counts = Counter()
    post_urls = []

    for req in captured_requests:
        # Extract domain + path (no query params)
        url = req["url"].split("?")[0]
        url_counts[url] += 1
        if req["method"] == "POST":
            post_urls.append(req)

    print(f"\nTotal requests: {len(captured_requests)}")
    print(f"POST requests: {len(post_urls)}")

    print("\n--- ALL UNIQUE URLS (by frequency) ---")
    for url, count in url_counts.most_common():
        print(f"  [{count:3d}x] {url}")

    print("\n--- POST REQUESTS (most likely time-tracking candidates) ---")
    for req in post_urls:
        print(f"\n  {req['method']} {req['url']}")
        if req.get("post_data"):
            # Pretty print if JSON
            try:
                data = json.loads(req["post_data"])
                print(f"  BODY: {json.dumps(data, indent=4)}")
            except (json.JSONDecodeError, TypeError):
                print(f"  BODY: {req['post_data'][:500]}")
        if req.get("status"):
            print(f"  STATUS: {req['status']}")
        if req.get("response_body"):
            body = req["response_body"]
            try:
                parsed = json.loads(body)
                print(f"  RESPONSE: {json.dumps(parsed, indent=4)[:500]}")
            except (json.JSONDecodeError, TypeError):
                print(f"  RESPONSE: {body[:500]}")

    print("\n" + "=" * 70)
    print(f"Full capture saved to: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
