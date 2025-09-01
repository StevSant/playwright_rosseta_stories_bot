import time
import os
import dotenv
from playwright.sync_api import (
    Playwright,
    sync_playwright,
    Browser,
    BrowserContext,
    Page,
)
from typing import Optional


import os
from dotenv import load_dotenv


class RosettaStoneBot:
    def __init__(
        self, email: str, password: str, slow_mo: int = 500, headless: bool = False
    ):
        self.email = email
        self.password = password
        self.slow_mo = slow_mo
        self.headless = headless

        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def launch_browser(self, playwright: Playwright):
        """Inicializa el navegador y el contexto con permisos bloqueados."""
        self.browser = playwright.chromium.launch(
            headless=self.headless, slow_mo=self.slow_mo
        )
        self.context = self.browser.new_context(permissions=[], accept_downloads=True)
        self.page = self.context.new_page()
        print("[INFO] Navegador iniciado.")

    def login(self):
        """Realiza el login en Rosetta Stone."""
        print("[INFO] Abriendo página de login...")
        self.page.goto("https://login.rosettastone.com/login")

        print("[INFO] Rellenando correo electrónico...")
        self.page.get_by_role("textbox", name="Email address").fill(self.email)
        self.page.get_by_role("textbox", name="Email address").press("Tab")

        print("[INFO] Rellenando contraseña...")
        self.page.get_by_role("textbox", name="Password").fill(self.password)

        print("[INFO] Marcando 'Remember?'...")
        self.page.get_by_text("Remember?").click()

        print("[INFO] Haciendo click en 'Sign in'...")
        self.page.get_by_role("button", name="Sign in").click()

    def navigate_to_lesson(self):
        """Navega hasta la lección específica a reproducir."""
        print("[INFO] Entrando en 'Foundations'...")
        self.page.get_by_text("Foundations").click()

        print("[INFO] Explorando todo el contenido...")
        self.page.get_by_text("Explorar todo el contenido").click()

        print("[INFO] Seleccionando segunda lección...")
        self.page.locator("a").nth(1).click()

        print("[INFO] Haciendo click en la lección específica...")
        self.page.locator(
            "div:nth-child(6) > div:nth-child(2) > .css-3bo236 > div > .css-djy551 > .css-a9mqkc > .css-vl4mjm"
        ).click()

        print("[INFO] Esperando y haciendo click en 'Continuar sin voz'...")
        self.page.get_by_role("button", name="Continuar sin voz").wait_for(
            state="visible", timeout=60000
        )
        self.page.get_by_role("button", name="Continuar sin voz").click()

        print("[INFO] Seleccionando 'Escuchar'...")
        self.page.get_by_text("Escuchar").click()

        # Ignorar diálogos emergentes automáticamente
        self.page.on("dialog", lambda dialog: dialog.dismiss())
        print("[INFO] Diálogos emergentes configurados para ignorar automáticamente.")

    def activity_loop(self):
        """Bucle principal para mantener la lección activa."""
        print("[INFO] Iniciando bucle de actividad para mantener la lección activa...")
        try:
            while True:
                print("[LOOP] Reproduciendo audio...")
                self.page.locator("polygon").nth(3).click()
                time.sleep(50)

                print("[LOOP] Retrocediendo 10 segundos...")
                self.page.get_by_text("10").click()
                time.sleep(5)

                print("[LOOP] Pausando...")
                self.page.locator("rect").nth(1).click()
                time.sleep(5)

                print("[LOOP] Acciones secundarias: Leer y Escuchar...")
                self.page.get_by_text("Leer").click()
                time.sleep(5)
                self.page.get_by_text("Escuchar").click()
                time.sleep(5)

                print("[LOOP] Ciclo completado, repitiendo...")

        except KeyboardInterrupt:
            print("[INFO] Bucle interrumpido por el usuario.")

    def close_browser(self):
        """Cierra la página, contexto y navegador."""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        print("[INFO] Navegador cerrado, script terminado.")


def main():
    load_dotenv()

    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    # Allow overriding headless mode from environment for containerized runs.
    # PLAYWRIGHT_HEADLESS: set to '0', 'false', or 'no' to disable headless. Default is headless.
    headless_env = os.getenv("PLAYWRIGHT_HEADLESS", "1")
    headless = headless_env.lower() not in ("0", "false", "no")

    with sync_playwright() as playwright:
        bot = RosettaStoneBot(email, password, slow_mo=500, headless=headless)
        bot.launch_browser(playwright)
        bot.login()
        bot.navigate_to_lesson()
        bot.activity_loop()
        bot.close_browser()


if __name__ == "__main__":
    main()
