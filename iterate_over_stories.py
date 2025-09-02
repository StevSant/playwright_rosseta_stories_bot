import re
import time
from playwright.sync_api import Playwright, sync_playwright


def run(playwright: Playwright) -> None:
    print("[INFO] Lanzando navegador...")
    browser = playwright.chromium.launch(
        headless=False,
        slow_mo=100,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-default-browser-check",
            "--disable-dev-shm-usage",
        ],
    )
    context = browser.new_context(
        permissions=[],
        accept_downloads=True,
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),
        locale="es-ES",
        viewport={"width": 1366, "height": 768},
    )
    page = context.new_page()

    # LOGIN
    print("[INFO] Accediendo a la página de login...")
    page.goto("https://login.rosettastone.com/login")
    print(f"[DEBUG] URL actual: {page.url}")

    print("[INFO] Ingresando correo electrónico...")
    page.get_by_role("textbox", name="Email address").fill(
        "e1315269017@live.uleam.edu.ec"
    )

    print("[INFO] Ingresando contraseña...")
    page.get_by_role("textbox", name="Password").fill("Nicolromero2006")

    print("[INFO] Marcando 'Remember' y enviando formulario...")
    page.get_by_role("checkbox", name="Remember").check()
    page.get_by_role("button", name="Sign in").click()

    # Espera post login
    page.wait_for_load_state("networkidle")
    print(f"[DEBUG] URL tras login: {page.url}")
    print(f"[DEBUG] Título de página: {page.title()}")

    # Navegar a contenido
    try:
        page.get_by_role("listitem").click()
        print("[DEBUG] Click en primer 'listitem' exitoso.")
    except Exception as e:
        print(f"[ERROR] No se pudo clicar 'listitem': {e}")

    try:
        page.get_by_text("Explorar todo el contenido").click()
        print("[DEBUG] Click en 'Explorar todo el contenido' exitoso.")
    except Exception as e:
        print(f"[ERROR] No se encontró 'Explorar todo el contenido': {e}")

    try:
        page.locator("a").nth(1).click()
        print("[DEBUG] Click en link de navegación exitoso.")
    except Exception as e:
        print(f"[ERROR] No se pudo clicar en link: {e}")

    # Esperamos a que cargue la sección
    time.sleep(4)
    print(f"[DEBUG] URL en sección Historias (esperada): {page.url}")
    print(f"[DEBUG] Título de página: {page.title()}")

    # Obtener todas las cards visibles
    print("[INFO] Obteniendo todas las cards de Historias...")
    cards = page.locator("div[data-qa^='BookCover-']")
    total_cards = cards.count()
    print(f"[INFO] Se encontraron {total_cards} cards.")

    # Si no encuentra cards, probamos a mostrar debug de otros divs sospechosos
    if total_cards == 0:
        fallback = page.locator("div")
        print(f"[DEBUG] Total de <div> en la página: {fallback.count()}")
        print(
            "[SUGERENCIA] Abre DevTools en esa página y revisa la clase exacta de las cards."
        )

    for i in range(total_cards):
        title = cards.nth(i).inner_text(timeout=5000).strip()
        print(f"    [CARD {i+1}] {title}")
        print(f"[INFO] Accediendo a la card {i+1}/{total_cards}...")

        # Localizar la card actual
        try:
            card = cards.nth(i)
            card.scroll_into_view_if_needed()
            card.click()
            print(f"[DEBUG] Click en card {i+1} exitoso.")
            time.sleep(1)
        except Exception as e:
            print(f"[ERROR] No se pudo clicar la card {i+1}: {e}")
            continue

        # Flujo dentro de la lección
        try:
            page.get_by_role("button", name="Continuar sin voz").click()
            print("[DEBUG] Botón 'Continuar sin voz' clickeado.")
        except:
            print("[DEBUG] No apareció 'Continuar sin voz'.")

        try:
            page.get_by_text("Escuchar").click()
            print("[DEBUG] Botón 'Escuchar' clickeado.")
        except:
            print("[DEBUG] No apareció 'Escuchar'.")

        try:
            page.locator("polygon").nth(3).click()
            print("[DEBUG] Botón 'Siguiente' clickeado.")
        except:
            print("[DEBUG] No se pudo avanzar con 'polygon'.")

        try:
            page.locator("circle").click()
            print("[DEBUG] Botón 'circle' clickeado.")
        except:
            print("[DEBUG] No se encontró botón 'circle'.")

        # Volver a la lista de historias
        try:
            page.locator("div").filter(has_text=re.compile(r"^Historias$")).click()
            print("[DEBUG] Regresando a Historias.")
            page.wait_for_load_state("networkidle")
            time.sleep(1)
        except:
            print("[ERROR] No se pudo regresar a la lista de Historias.")

    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
