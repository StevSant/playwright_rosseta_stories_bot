import re
from playwright.sync_api import Page

from . import utils
from .constants import URLs, CompiledPatterns


class AuthenticationService:
    """Handles user authentication for Rosetta Stone."""

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password

    def login(self, page: Page) -> None:
        """Perform login to Rosetta Stone with resilient selectors."""
        print("[INFO] Opening login page...")
        page.goto(URLs.LOGIN_URL)
        page.wait_for_load_state("networkidle")

        utils.click_cookie_consent_if_present(page)
        utils.debug_dump(page, "login_page")

        self._fill_email(page)
        self._fill_password(page)
        self._submit_form(page)
        self._verify_login_success(page)

    def _fill_email(self, page: Page) -> None:
        """Fill the email field with error handling."""
        print("[INFO] Filling email address...")

        email_selectors = (
            "input[type='email'], input[name='email'], input#email, "
            "input[autocomplete='username'], input[autocomplete='email'], "
            "input[placeholder='Email address'], [data-qa='Email']"
        )

        _, email_locator = utils.find_in_any_frame(page, email_selectors)

        if not email_locator:
            _, email_locator = utils.find_in_any_frame(
                page,
                "input[type='text'][name='email'], input[type='text'][autocomplete='username']",
            )

        if not email_locator:
            current_url = page.url
            print(f"[ERROR] Email field not found. Current URL: {current_url}")
            utils.debug_dump(page, "no_email")
            raise RuntimeError("Email field not found on page or in iframes")

        email_locator.fill(self.email)

    def _fill_password(self, page: Page) -> None:
        """Fill the password field with error handling."""
        print("[INFO] Filling password...")

        pwd_selectors = (
            "input[type='password'], input[name='password'], input#password, "
            "input[autocomplete='current-password'], [data-qa='Password'], "
            "input[placeholder='Password']"
        )

        _, password_locator = utils.find_in_any_frame(page, pwd_selectors)

        if not password_locator:
            current_url = page.url
            print(f"[ERROR] Password field not found. Current URL: {current_url}")
            utils.debug_dump(page, "no_password")
            raise RuntimeError("Password field not found on page or in iframes")

        password_locator.fill(self.password)

    def _submit_form(self, page: Page) -> None:
        """Submit the login form using multiple strategies."""
        print("[INFO] Submitting form (Enter)...")

        # Try pressing Enter on password field
        try:
            pwd_selectors = (
                "input[type='password'], input[name='password'], input#password"
            )
            _, password_locator = utils.find_in_any_frame(page, pwd_selectors)
            if password_locator:
                password_locator.press("Enter")
        except Exception:
            pass

        # Try clicking submit button
        try:
            sign_btn = page.locator(
                "[data-qa='SignInButton'], button[type='submit']"
            ).first
            sign_btn.wait_for(state="visible", timeout=5000)
            sign_btn.click(timeout=5000)
        except Exception:
            pass

        # Wait for navigation
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

    def _verify_login_success(self, page: Page) -> None:
        """Verify if login was successful and handle account selection if needed."""
        print("[INFO] Verifying login success...")
        try:
            title = page.title() or ""
        except Exception:
            title = ""

        # Check if we need to handle institutional account selection
        if self._handle_institutional_account_selection(page):
            return

        if re.search(r"login|signin|acceder|entrar|iniciar", title, re.I):
            print("[WARN] Still on login page, trying button click...")
            self._retry_login_button_click(page)

        # Final debug dump after login attempts
        try:
            utils.debug_dump(page, "logged_in")
        except Exception:
            pass

    def _retry_login_button_click(self, page: Page) -> None:
        """Retry clicking login button with multiple strategies."""
        try:
            btn = page.get_by_role("button").filter(has_text=CompiledPatterns.SIGNIN)
            btn.first.click(timeout=10000)
        except Exception:
            self._try_frame_login_buttons(page)

    def _try_frame_login_buttons(self, page: Page) -> None:
        """Try clicking login buttons in frames."""
        clicked = False
        for frame in page.frames:
            try:
                fbtn = frame.get_by_role("button").filter(
                    has_text=CompiledPatterns.SIGNIN
                )
                fbtn.first.click(timeout=5000)
                clicked = True
                break
            except Exception:
                continue

        if not clicked:
            try:
                page.locator("button[type='submit'], input[type='submit']").first.click(
                    timeout=5000
                )
            except Exception:
                pass

    def _handle_institutional_account_selection(self, page: Page) -> bool:
        """Handle institutional account selection if multiple accounts are associated."""
        try:
            # Wait a moment for the page to load after initial login attempt
            page.wait_for_load_state("networkidle", timeout=5000)

            # Check if we're on an account selection page by looking for institutional indicators
            # Look for "uleam" text or similar institutional selectors
            institutional_selectors = [
                "text=uleam",
                "[data-testid*='uleam']",
                "button:has-text('uleam')",
                "div:has-text('uleam')",
                "span:has-text('uleam')",
            ]

            account_found = False
            for selector in institutional_selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible(timeout=3000):
                        print("[INFO] Found institutional account selector (uleam)...")
                        element.click(timeout=5000)
                        account_found = True
                        break
                except Exception:
                    continue

            if not account_found:
                # Try looking for any institutional account indicators in the page content
                page_content = page.content().lower()
                if (
                    "uleam" in page_content
                    or "universidad" in page_content
                    or "institution" in page_content
                ):
                    print(
                        "[INFO] Detected institutional account page, looking for clickable elements..."
                    )
                    try:
                        # Try clicking on any element containing "uleam"
                        uleam_element = page.get_by_text("uleam", exact=False).first
                        uleam_element.click(timeout=5000)
                        account_found = True
                    except Exception:
                        pass

            if account_found:
                print("[INFO] Selected institutional account, re-entering password...")
                # Wait for the page to load after account selection
                page.wait_for_load_state("networkidle", timeout=8000)

                # Re-enter password
                self._fill_password(page)
                self._submit_form(page)

                # Wait for final navigation
                page.wait_for_load_state("networkidle", timeout=10000)

                # Debug dump after institutional login
                try:
                    utils.debug_dump(page, "institutional_login_complete")
                except Exception:
                    pass

                return True

        except Exception as e:
            print(f"[WARN] Error during institutional account handling: {e}")

        return False
