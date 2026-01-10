"""Login Page Object following Page Object Model pattern."""

import re
from typing import Optional

from playwright.sync_api import Page, Locator

from .base_page import BasePage
from ..locators import LoginLocators
from ..components import CookieConsent
from ..core import Timeouts


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

        # Try clicking submit button
        try:
            submit_btn = self.submit_button
            if self.wait_for_element(submit_btn, timeout=Timeouts.DEFAULT_TIMEOUT):
                self.click_safe(submit_btn, scroll=False)
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

        Args:
            password: User password (needed for institutional re-auth)

        Returns:
            True if login successful, False otherwise
        """
        self._log("Verifying login success...")

        try:
            title = self.title
        except Exception:
            title = ""

        # Handle institutional account selection if needed
        if self._handle_institutional_account(password):
            return True

        # Check if still on login page
        if self._locators.LOGIN_PAGE_PATTERN.search(title):
            self._log("Still on login page, retrying button click...", level="WARN")
            self._retry_login_click()

        self.take_screenshot("logged_in")
        return True

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
