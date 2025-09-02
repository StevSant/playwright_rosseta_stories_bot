import re
from pathlib import Path
from typing import Optional, Tuple, Union

from playwright.sync_api import Page, Frame, Locator


def debug_dump(page: Optional[Page], tag: str = "state"):
    """Guarda HTML, screenshot y un pequeño txt con info de la página/frames."""
    try:
        dbg = Path("debug")
        dbg.mkdir(exist_ok=True)
        # Archivo para mantener un contador persistente entre ejecuciones
        idx_file = dbg / ".dump_index"
        try:
            last = int(idx_file.read_text(encoding="utf-8").strip() or "0")
        except Exception:
            last = 0
        current = last + 1
        try:
            idx_file.write_text(str(current), encoding="utf-8")
        except Exception:
            # Si no se puede escribir el índice, seguimos sin fallo crítico
            pass

        # Sanitizar el tag para nombres de archivo legibles
        safe_tag = re.sub(r"[^0-9A-Za-z_.-]", "_", tag).strip("_")
        base_name = f"{current}.{safe_tag}" if safe_tag else str(current)
        info = []
        if page is not None:
            info = [
                f"URL: {page.url}",
                f"Title: {page.title()}",
                f"Frames: {len(page.frames)}",
            ]
            for i, fr in enumerate(page.frames):
                try:
                    info.append(f"  [{i}] name={fr.name} url={fr.url}")
                except Exception:
                    pass
            page.screenshot(path=str(dbg / f"{base_name}.png"), full_page=True)
            print(f"[DEBUG] Dump guardado en carpeta 'debug' con base '{base_name}'.")
        else:
            info = ["[DEBUG] page is None, no dump created."]
            (dbg / f"{base_name}.txt").write_text("\n".join(info), encoding="utf-8")
    except Exception as e:
        print(f"[DEBUG] Falló dump de depuración: {e}")


def click_cookie_consent_if_present(page: Optional[Page]):
    """Intenta aceptar o cerrar banners de cookies comunes."""
    if page is None:
        return
    try:
        btn = page.get_by_role("button").filter(
            has_text=re.compile(
                r"accept|agree|allow|ok|got\s*it|entendido|acept(ar|o)|permit(ir|o)|de\s*acuerdo",
                re.I,
            )
        )
        btn.first.click(timeout=3000)
        print("[INFO] Banner de cookies aceptado.")
    except Exception:
        try:
            page.locator(
                "button[aria-label='Close'], [data-testid='close']"
            ).first.click(timeout=2000)
            print("[INFO] Banner de cookies cerrado.")
        except Exception:
            pass


def find_in_any_frame(
    page: Optional[Page], selector: str
) -> Tuple[Optional[Union[Frame, Page]], Optional[Locator]]:
    """Busca un locator visible por CSS en la página o en cualquiera de sus iframes.

    Devuelve (frame_or_page, locator) o (None, None) si no se encuentra.
    """
    if page is None:
        return None, None

    # Página principal
    try:
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=3000)
        return page, loc
    except Exception:
        pass

    # Frames
    for frame in page.frames:
        try:
            floc = frame.locator(selector).first
            floc.wait_for(state="visible", timeout=1500)
            return frame, floc
        except Exception:
            continue

    return None, None
