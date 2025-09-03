"""Authentication service for Rosetta Stone."""

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
        """Verify if login was successful and retry if needed."""
        try:
            title = page.title() or ""
        except Exception:
            title = ""

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
