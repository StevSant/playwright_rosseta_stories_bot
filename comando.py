import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://login.rosettastone.com/login")
    page.get_by_role("textbox", name="Email address").fill("e1351084163@live.uleam.edu.ec")
    page.get_by_role("textbox", name="Email address").press("Tab")
    page.get_by_role("textbox", name="Password").fill("cori2005")
    page.get_by_role("checkbox", name="Remember").check()
    page.get_by_role("button", name="Sign in").click()
    page.get_by_text("Foundations").click()
    page.get_by_text("Explorar todo el contenido").click()
    page.locator("a").nth(1).click()
    page.locator("circle").click()
    page.locator("circle").click()
    page.locator("circle").click()
    page.locator("circle").click()
    page.locator("circle").click()
    page.locator("circle").click()
    page.locator("polygon").nth(3).click()
    page.locator("rect").nth(1).click()
    page.locator("polygon").nth(3).click()
    expect(page.locator("circle")).to_be_visible()
    page.locator("rect").nth(2).click()
    page.locator("polygon").nth(3).click()
    page.locator("rect").nth(2).click()
    page.locator("polygon").nth(3).click()
    page.locator("rect").nth(2).click()
    page.locator("polygon").nth(3).click()
    page.locator("rect").nth(2).click()
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.locator("span:nth-child(472) > .css-1psylr4 > .css-1wdbcre").click()
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
