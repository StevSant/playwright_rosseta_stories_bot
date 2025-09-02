import re
import time
from typing import Optional

from playwright.sync_api import (
    Playwright,
    Browser,
    BrowserContext,
    Page,
)

from . import utils


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
        try:
            self.browser = playwright.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-default-browser-check",
                    "--disable-dev-shm-usage",
                ],
            )
        except Exception:
            # Fallback por si alguna flag falla
            self.browser = playwright.chromium.launch(
                headless=self.headless, slow_mo=self.slow_mo
            )

        # Contexto con un user-agent realista y locale
        self.context = self.browser.new_context(
            permissions=[],
            accept_downloads=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
            viewport={"width": 1366, "height": 768},
        )
        self.page = self.context.new_page()
        print("[INFO] Navegador iniciado.")

    def login(self):
        """Realiza el login en Rosetta Stone con selectores resilientes (ES/EN)."""
        print("[INFO] Abriendo página de login...")
        self.page.goto("https://login.rosettastone.com/login")
        self.page.wait_for_load_state("networkidle")
        utils.click_cookie_consent_if_present(self.page)
        utils.debug_dump(self.page, "login_page")

        print("[INFO] Rellenando correo electrónico...")
        email_selectors = (
            "input[type='email'], input[name='email'], input#email, "
            "input[autocomplete='username'], input[autocomplete='email'], "
            "input[placeholder='Email address'], [data-qa='Email']"
        )
        _, email_locator = utils.find_in_any_frame(self.page, email_selectors)
        if not email_locator:
            _, email_locator = utils.find_in_any_frame(
                self.page,
                "input[type='text'][name='email'], input[type='text'][autocomplete='username']",
            )
        if not email_locator:
            current_url = self.page.url
            print(f"[ERROR] No se encontró el campo email. URL actual: {current_url}")
            utils.debug_dump(self.page, "no_email")
            raise RuntimeError(
                "No se encontró el campo de email en la página o en iframes"
            )
        email_locator.fill(self.email)

        print("[INFO] Rellenando contraseña...")
        pwd_selectors = (
            "input[type='password'], input[name='password'], input#password, "
            "input[autocomplete='current-password'], [data-qa='Password'], input[placeholder='Password']"
        )
        _, password_locator = utils.find_in_any_frame(self.page, pwd_selectors)
        if not password_locator:
            current_url = self.page.url
            print(
                f"[ERROR] No se encontró el campo password. URL actual: {current_url}"
            )
            utils.debug_dump(self.page, "no_password")
            raise RuntimeError(
                "No se encontró el campo de password en la página o en iframes"
            )
        password_locator.fill(self.password)

        print("[INFO] Enviando formulario (Enter)...")
        try:
            password_locator.press("Enter")
        except Exception:
            pass

        try:
            sign_btn = self.page.locator(
                "[data-qa='SignInButton'], button[type='submit']"
            ).first
            sign_btn.wait_for(state="visible", timeout=5000)
            sign_btn.click(timeout=5000)
        except Exception:
            pass

        try:
            self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        try:
            _title = self.page.title() or ""
        except Exception:
            _title = ""
        if re.search(r"login|signin|acceder|entrar|iniciar", _title, re.I):
            print("[WARN] Parece que seguimos en login, intentando click en botón...")
            try:
                btn = self.page.get_by_role("button").filter(
                    has_text=re.compile(
                        r"sign\s*in|iniciar\s*sesión|acceder|entrar|login", re.I
                    )
                )
                btn.first.click(timeout=10000)
            except Exception:
                clicked = False
                for frame in self.page.frames:
                    try:
                        fbtn = frame.get_by_role("button").filter(
                            has_text=re.compile(
                                r"sign\s*in|iniciar\s*sesión|acceder|entrar|login", re.I
                            )
                        )
                        fbtn.first.click(timeout=5000)
                        clicked = True
                        break
                    except Exception:
                        continue
                if not clicked:
                    try:
                        self.page.locator(
                            "button[type='submit'], input[type='submit']"
                        ).first.click(timeout=5000)
                    except Exception:
                        pass
        # Dump tras intentar el login (estado después de los intentos)
        try:
            utils.debug_dump(self.page, "logged_in")
        except Exception:
            pass

    def navigate_to_lesson(self):
        """Navega hasta la lección específica a reproducir y toma screenshots claves."""
        print("[INFO] Entrando en 'Foundations/Fundamentos'...")
        self.page.get_by_text(re.compile(r"Foundations|Fundamentos", re.I)).click()
        utils.debug_dump(self.page, "foundations")

        print("[INFO] Explorando todo el contenido / Browse all content...")
        self.page.get_by_text(
            re.compile(
                r"Explorar todo el contenido|Browse all content|Explore all content",
                re.I,
            )
        ).click()
        utils.debug_dump(self.page, "browse_all_content")

        print("[INFO] Seleccionando segunda lección...")
        self.page.locator("a").nth(1).click()
        utils.debug_dump(self.page, "selected_second_lesson")

        print("[INFO] Haciendo click en la lección específica...")
        self.page.locator(
            "div:nth-child(6) > div:nth-child(2) > .css-3bo236 > div > .css-djy551 > .css-a9mqkc > .css-vl4mjm"
        ).click()
        utils.debug_dump(self.page, "entered_specific_lesson")

        print(
            "[INFO] Esperando y haciendo click en 'Continuar sin voz / Continue without voice'..."
        )
        cont_btn = self.page.get_by_role("button").filter(
            has_text=re.compile(r"Continuar sin voz|Continue without voice", re.I)
        )
        cont_btn.first.wait_for(state="visible", timeout=60000)
        cont_btn.first.click()
        utils.debug_dump(self.page, "continue_without_voice")

        print("[INFO] Seleccionando 'Escuchar/Listen'...")
        self.page.get_by_text(re.compile(r"Escuchar|Listen", re.I)).click()
        utils.debug_dump(self.page, "listen_mode")

        self.page.on("dialog", lambda dialog: dialog.dismiss())
        print("[INFO] Diálogos emergentes configurados para ignorar automáticamente.")

    def activity_loop(self):
        """Bucle principal para mantener la lección activa. Toma una captura antes de iniciar."""
        print("[INFO] Iniciando bucle de actividad para mantener la lección activa...")
        utils.debug_dump(self.page, "before_activity_loop")
        iter_count = 0
        try:
            while True:
                iter_count += 1
                print(f"[LOOP] Iteración {iter_count}: Reproduciendo audio...")
                try:
                    self.page.locator("polygon").nth(3).click()
                except Exception:
                    print(
                        "[WARN] No se encontró el control de reproducción (polygon) en esta iteración."
                    )


                time.sleep(50)
                # Guardar una captura en las primeras iteraciones para facilitar debug
                try:
                    if iter_count <= 3:
                        utils.debug_dump(self.page, f"activity_iter_{iter_count}")
                except Exception:
                    pass

                print("[LOOP] Retrocediendo 10 segundos...")
                try:
                    self.page.get_by_text("10").click()
                except Exception:
                    pass
                time.sleep(5)

                print("[LOOP] Pausando...")
                try:
                    self.page.locator("rect").nth(1).click()
                except Exception:
                    pass
                time.sleep(5)

                print("[LOOP] Acciones secundarias: Leer/Read y Escuchar/Listen...")
                try:
                    self.page.get_by_text(re.compile(r"Leer|Read", re.I)).click()
                    time.sleep(5)
                    self.page.get_by_text(re.compile(r"Escuchar|Listen", re.I)).click()
                except Exception:
                    pass
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
