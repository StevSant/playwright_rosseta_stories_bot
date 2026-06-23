"""Login Page Object following Page Object Model pattern."""

import time
from typing import Optional

from playwright.sync_api import Page, Locator

from .base_page import BasePage
from ..locators import LoginLocators
from ..components import CookieConsent
from ..core import (
    MANUAL_LOGIN_HINT,
    Timeouts,
    find_login_blocker,
    is_kmsi_prompt,
    is_login_url,
)


class LoginPage(BasePage):
    """
    Page Object for the Rosetta Stone login page.

    Handles all login-related interactions including:
    - Credential input
    - Form submission
    - Institutional account selection
    - Login verification
    """

    def __init__(self, page: Page, debug_enabled: bool = False):
        """
        Initialize the Login Page.

        Args:
            page: Playwright Page object
            debug_enabled: Whether to enable debug screenshots
        """
        super().__init__(page, debug_enabled)
        self._locators = LoginLocators()
        self._cookie_consent = CookieConsent(page, debug_enabled)

    # ==================== Properties ====================

    @property
    def email_field(self) -> Optional[Locator]:
        """Get the email input field locator."""
        locator = self.find_in_frames(self._locators.EMAIL_SELECTORS)
        if not locator:
            locator = self.find_in_frames(self._locators.EMAIL_FALLBACK_SELECTORS)
        return locator

    @property
    def password_field(self) -> Optional[Locator]:
        """Get the password input field locator."""
        return self.find_in_frames(self._locators.PASSWORD_SELECTORS)

    @property
    def submit_button(self) -> Locator:
        """Get the submit button locator."""
        return self._page.locator(self._locators.SUBMIT_BUTTON).first

    # ==================== Actions ====================

    def open(self) -> "LoginPage":
        """Navigate to the login page."""
        self._log("Opening login page...")
        self.navigate_to(self._locators.LOGIN_URL)
        self.wait_for_load()
        self._cookie_consent.dismiss_if_present()
        self.take_screenshot("login_page")
        return self

    def login(self, email: str, password: str) -> bool:
        """
        Perform complete login flow.

        Args:
            email: User email address
            password: User password

        Returns:
            True if login was successful, False otherwise
        """
        self.open()

        # A restored storage_state session redirects straight into the app.
        if not is_login_url(self.url):
            self._log("Already logged in (restored session).")
            self.take_screenshot("already_logged_in")
            return True

        if not self._fill_email(email):
            return False

        if not self._fill_password(password):
            return False

        self._submit_form()

        return self._verify_login_success(password)

    def _fill_email(self, email: str) -> bool:
        """
        Fill the email field.

        Args:
            email: Email address to enter

        Returns:
            True if successful, False otherwise
        """
        self._log("Filling email address...")

        email_locator = self.email_field
        if not email_locator:
            self._log(f"Email field not found. Current URL: {self.url}", level="ERROR")
            self.take_screenshot("no_email")
            return False

        return self.fill_safe(email_locator, email)

    def _fill_password(self, password: str) -> bool:
        """
        Fill the password field.

        Args:
            password: Password to enter

        Returns:
            True if successful, False otherwise
        """
        self._log("Filling password...")

        password_locator = self.password_field
        if not password_locator:
            self._log(
                f"Password field not found. Current URL: {self.url}", level="ERROR"
            )
            self.take_screenshot("no_password")
            return False

        return self.fill_safe(password_locator, password)

    def _submit_form(self) -> None:
        """Submit the login form using multiple strategies."""
        self._log("Submitting form...")

        # Try pressing Enter on password field
        try:
            password_locator = self.password_field
            if password_locator:
                password_locator.press("Enter")
        except Exception:
            pass

        # Try clicking submit button (wait for it to be enabled)
        try:
            submit_btn = self.submit_button
            if self.wait_for_element(submit_btn, timeout=Timeouts.LONG_TIMEOUT):
                self.click_safe(
                    submit_btn,
                    scroll=False,
                    wait_enabled=True,
                    timeout=Timeouts.LONG_TIMEOUT,
                )
        except Exception:
            pass

        # Wait for navigation
        try:
            self.wait_for_load(timeout=Timeouts.LONG_TIMEOUT)
        except Exception:
            pass

    def _verify_login_success(self, password: str) -> bool:
        """
        Verify if login was successful.

        Unlike the old implementation (which always returned True and let the
        failure surface much later as ``login?reauth=true`` redirects), this
        actually waits until the browser leaves every login/Microsoft page.
        If it never does, it reports the blocking screen (MFA, CAPTCHA,
        wrong password...) and fails loudly.

        Args:
            password: User password (needed for institutional re-auth)

        Returns:
            True if login successful, False otherwise
        """
        self._log("Verifying login success...")

        # Handle institutional account selection if needed (best-effort; the
        # URL check below is the real verdict).
        self._handle_institutional_account(password)
        self._handle_stay_signed_in()

        if self._wait_until_authenticated(timeout_sec=20):
            self.take_screenshot("logged_in")
            return True

        # Still on a login page: retry the submit once, then re-check.
        self._log("Still on login page, retrying button click...", level="WARN")
        self._retry_login_click()
        self._handle_stay_signed_in()

        if self._wait_until_authenticated(timeout_sec=15):
            self.take_screenshot("logged_in")
            return True

        blocker = self._detect_login_blocker()
        if blocker:
            self._log(f"Login blocked: {blocker}", level="ERROR")
        self._log(
            f"Login did not complete - still on {self.url}. {MANUAL_LOGIN_HINT}",
            level="ERROR",
        )
        self.take_screenshot("login_failed")
        return False

    def _wait_until_authenticated(self, timeout_sec: int) -> bool:
        """Poll until the URL leaves every login/authentication page."""
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                if not is_login_url(self.url):
                    return True
            except Exception:
                pass
            self.wait(1)
        return False

    def _detect_login_blocker(self) -> Optional[str]:
        """Identify the verification/MFA/error screen blocking the login."""
        try:
            return find_login_blocker(self._page.inner_text("body"))
        except Exception:
            return None

    def _handle_stay_signed_in(self) -> None:
        """Accept Microsoft's 'Stay signed in?' (KMSI) prompt if shown."""
        try:
            if not is_kmsi_prompt(self._page.inner_text("body")):
                return
        except Exception:
            return

        self._log("Accepting 'Stay signed in?' prompt...")
        try:
            checkbox = self._page.locator("#KmsiCheckboxField").first
            if self.is_visible(checkbox, timeout=1500):
                checkbox.check()
        except Exception:
            pass

        for selector in (
            "#idSIButton9",
            "input[type='submit'][value='Yes']",
            "input[type='submit'][value='Sí']",
            "button:has-text('Yes')",
            "button:has-text('Sí')",
        ):
            try:
                btn = self._page.locator(selector).first
                if self.is_visible(btn, timeout=1500):
                    btn.click()
                    self.wait(2)
                    return
            except Exception:
                continue

    def _handle_institutional_account(self, password: str) -> bool:
        """
        Handle institutional account selection if present.

        Args:
            password: Password for re-authentication

        Returns:
            True if institutional account was handled, False otherwise
        """
        try:
            self.wait_for_load(timeout=Timeouts.DEFAULT_TIMEOUT)

            # Look for institutional selectors
            for selector in self._locators.INSTITUTIONAL_SELECTORS:
                try:
                    element = self._page.locator(selector).first
                    if self.is_visible(element, timeout=Timeouts.SHORT_TIMEOUT):
                        self._log("Found institutional account selector...")
                        self.click_safe(element)

                        # Re-enter password after account selection
                        self._log("Re-entering password for institutional account...")
                        self.wait_for_load()
                        self._fill_password(password)
                        self._submit_form()
                        self.wait_for_load()

                        self.take_screenshot("institutional_login_complete")
                        return True
                except Exception:
                    continue

            # Check page content for institutional indicators
            page_content = self._page.content().lower()
            if any(
                ind in page_content for ind in ["uleam", "universidad", "institution"]
            ):
                self._log("Detected institutional page, looking for account...")
                try:
                    uleam_element = self._page.get_by_text("uleam", exact=False).first
                    self.click_safe(uleam_element)

                    self.wait_for_load()
                    self._fill_password(password)
                    self._submit_form()
                    self.wait_for_load()

                    return True
                except Exception:
                    pass

        except Exception as e:
            self._log(f"Error during institutional account handling: {e}", level="WARN")

        return False

    def _retry_login_click(self) -> None:
        """Retry clicking login button with multiple strategies."""
        try:
            btn = self._page.get_by_role("button").filter(
                has_text=self._locators.SIGNIN_PATTERN
            )
            self.click_safe(btn.first, timeout=Timeouts.LONG_TIMEOUT)
        except Exception:
            self._try_frame_login_buttons()

    def _try_frame_login_buttons(self) -> None:
        """Try clicking login buttons in frames."""
        for frame in self._page.frames:
            try:
                btn = frame.get_by_role("button").filter(
                    has_text=self._locators.SIGNIN_PATTERN
                )
                btn.first.click(timeout=Timeouts.DEFAULT_TIMEOUT)
                return
            except Exception:
                continue

        # Last resort: try submit button
        try:
            self._page.locator(
                "button[type='submit'], input[type='submit']"
            ).first.click(timeout=Timeouts.DEFAULT_TIMEOUT)
        except Exception:
            pass
