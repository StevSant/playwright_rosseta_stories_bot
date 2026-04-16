"""
Debug script: login, go to Stories, take a screenshot, dump the page HTML,
and list all clickable elements to figure out how to enter a story.
"""

import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from playwright.async_api import async_playwright

env_file = sys.argv[1] if len(sys.argv) > 1 else ".env"
load_dotenv(env_file, override=True)

EMAIL = os.environ.get("EMAIL", "")
PASSWORD = os.environ.get("PASSWORD", "")


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


async def main():
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

        await fill(["input[type='email']", "input[autocomplete='email']"], EMAIL)
        pw = await fill(["input[type='password']", "input[name='password']"], PASSWORD)
        if pw:
            await asyncio.sleep(1)
            await pw.press("Enter")

        await asyncio.sleep(5)
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass

        # ULEAM
        try:
            content = await page.content()
            if "uleam" in content.lower():
                log("Selecting ULEAM...")
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

        # Foundations
        log("Going to Foundations...")
        try:
            el = page.get_by_text("Foundations", exact=False).first
            if not await el.is_visible(timeout=3000):
                el = page.get_by_text("Fundamentos", exact=False).first
            await el.click()
            await asyncio.sleep(8)
        except Exception:
            pass

        # Stories
        log("Going to Stories...")
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

        # Take screenshot
        await page.screenshot(path="debug_stories.png", full_page=True)
        log("Screenshot saved to debug_stories.png")

        # Dump all visible text elements
        log("\n=== VISIBLE TEXT ON PAGE ===")
        all_text = await page.locator("*:visible").all_text_contents()
        unique_texts = []
        for t in all_text:
            t = t.strip()
            if t and len(t) > 2 and len(t) < 200 and t not in unique_texts:
                unique_texts.append(t)

        for t in unique_texts[:50]:
            print(f"  '{t}'")

        # List all interactive elements
        log("\n=== CLICKABLE ELEMENTS ===")
        for selector in ["button", "a", "[role='button']", "[tabindex='0']", "[class*='card']", "[class*='Card']", "[class*='story']", "[class*='Story']"]:
            elements = page.locator(selector)
            count = await elements.count()
            if count > 0:
                print(f"\n  {selector}: {count} elements")
                for i in range(min(count, 5)):
                    el = elements.nth(i)
                    try:
                        text = (await el.text_content() or "").strip()[:80]
                        tag = await el.evaluate("el => el.tagName")
                        classes = await el.evaluate("el => el.className")
                        print(f"    [{i}] <{tag}> class='{classes[:60]}' text='{text}'")
                    except Exception:
                        pass

        # Also dump the outer HTML of the stories container
        log("\n=== STORIES CONTAINER HTML ===")
        try:
            # Try to find the main content area
            for sel in ["[class*='stories']", "[class*='Stories']", "#root", "main", "[role='main']"]:
                container = page.locator(sel).first
                try:
                    if await container.is_visible(timeout=1000):
                        html = await container.evaluate("el => el.outerHTML.substring(0, 3000)")
                        print(f"\n{sel}:")
                        print(html)
                        break
                except Exception:
                    continue
        except Exception:
            pass

        log("\nKeeping browser open for 15s for manual inspection...")
        await asyncio.sleep(15)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
