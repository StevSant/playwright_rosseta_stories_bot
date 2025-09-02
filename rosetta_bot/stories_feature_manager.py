"""Stories feature module for Rosetta Stone bot automation."""

import re
import time

from playwright.sync_api import Page

from .constants import WaitTimes


class StoriesFeatureManager:
    """Manages stories-related features and automation."""

    # Constante para el selector de regreso a Historias
    HISTORIAS_SELECTOR_PATTERN = r"^Historias$"

    def __init__(self, page: Page, debug_enabled: bool = False):
        """
        Initialize the Stories Feature Manager.

        Args:
            page: Playwright page object
            debug_enabled: Whether debug mode is enabled
        """
        self.page = page
        self.debug_enabled = debug_enabled

    def loop_all_histories(self) -> None:
        """
        Función principal que implementa la iteración infinita sobre todas las historias.

        En cada historia ejecuta la funcionalidad de intercalar entre escuchar y leer.
        Al finalizar una historia, vuelve automáticamente a la lista y continúa con la siguiente.
        Una vez que termine con la última historia, vuelve a comenzar desde la primera.
        """
        print("[INFO] Iniciando bucle infinito de historias...")

        # Navegar inicialmente a la sección de Historias
        if not self._navigate_to_stories_section():
            print("[ERROR] No se pudo acceder a la sección de Historias.")
            return

        iteration_count = 0

        try:
            while True:  # Bucle infinito
                iteration_count += 1
                print(f"[INFO] === Iteración completa #{iteration_count} ===")

                # Procesar todas las historias en esta iteración
                self._process_all_stories_once()

                print(
                    f"[INFO] Iteración #{iteration_count} completada. Reiniciando ciclo..."
                )
                time.sleep(WaitTimes.SHORT_WAIT)

        except KeyboardInterrupt:
            print("[INFO] Bucle infinito interrumpido por el usuario.")
        except Exception as e:
            print(f"[ERROR] Error en bucle infinito: {e}")

    def _process_all_stories_once(self) -> None:
        """Procesa todas las historias disponibles una vez."""
        print("[INFO] Procesando todas las historias disponibles...")

        # Obtener todas las cards visibles
        cards = self.page.locator("div[data-qa^='BookCover-']")
        total_cards = cards.count()
        print(f"[INFO] Se encontraron {total_cards} historias.")

        if total_cards == 0:
            print(
                "[WARN] No se encontraron historias. Verificando estructura de página..."
            )
            fallback = self.page.locator("div")
            print(f"[DEBUG] Total de <div> en la página: {fallback.count()}")
            return

        # Iterar sobre cada historia
        for i in range(total_cards):
            story_success = self._process_single_story(cards, i, total_cards)
            if not story_success:
                print(f"[WARN] Historia {i+1} no se pudo procesar completamente.")

            # Pausa breve entre historias
            time.sleep(WaitTimes.VERY_SHORT_WAIT)

    def _process_single_story(self, cards, index: int, total_cards: int) -> bool:
        """
        Procesa una historia individual con la funcionalidad de intercalar entre leer y escuchar.

        Args:
            cards: Locator de las cards de historias
            index: Índice de la historia actual
            total_cards: Número total de historias

        Returns:
            bool: True si se procesó exitosamente, False en caso contrario
        """
        try:
            # Obtener información de la historia
            title = cards.nth(index).inner_text(timeout=5000).strip()
            print(f"[INFO] === Historia {index+1}/{total_cards}: {title} ===")

            # Acceder a la historia
            card = cards.nth(index)
            card.scroll_into_view_if_needed()
            card.click()
            print(f"[DEBUG] Acceso a historia '{title}' exitoso.")
            time.sleep(WaitTimes.SHORT_WAIT)

            # Ejecutar la lógica de intercalar entre escuchar y leer
            self._execute_story_listen_read_cycle(title)

            # Volver a la lista de historias
            return self._return_to_stories_list()

        except Exception as e:
            print(f"[ERROR] Error procesando historia {index+1}: {e}")
            # Intentar regresar a la lista antes de continuar
            self._return_to_stories_list()
            return False

    def _execute_story_listen_read_cycle(self, story_title: str) -> None:
        """
        Ejecuta el ciclo de intercalar entre escuchar y leer en una historia.

        Args:
            story_title: Título de la historia para logging
        """
        print(f"[INFO] Iniciando ciclo escuchar/leer para '{story_title}'...")

        # Manejar botón "Continuar sin voz" si aparece
        self._handle_continue_without_voice()

        # Configurar el modo inicial (Escuchar)
        self._set_initial_listen_mode()

        # Ejecutar ciclo de actividades
        cycle_count = 0
        max_cycles = 5  # Límite para evitar bucles infinitos en una historia

        try:
            while cycle_count < max_cycles:
                cycle_count += 1
                print(f"[DEBUG] Ciclo {cycle_count} en historia '{story_title}'")

                # Reproducir audio
                self._play_audio()

                # Pausa para escuchar
                time.sleep(WaitTimes.ACTIVITY_CYCLE)

                # Intercalar entre leer y escuchar
                self._alternate_read_listen()

                # Verificar si la historia ha terminado o si debemos continuar
                if self._check_story_completion():
                    print(f"[INFO] Historia '{story_title}' completada.")
                    break

                time.sleep(WaitTimes.VERY_SHORT_WAIT)

        except Exception as e:
            print(f"[ERROR] Error en ciclo escuchar/leer para '{story_title}': {e}")

    def _handle_continue_without_voice(self) -> None:
        """Maneja el botón 'Continuar sin voz' si aparece."""
        try:
            continue_btn = self.page.get_by_role("button").filter(
                has_text=re.compile(r"Continuar sin voz|Continue without voice", re.I)
            )
            continue_btn.first.wait_for(state="visible", timeout=3000)
            continue_btn.first.click()
            print("[DEBUG] Botón 'Continuar sin voz' clickeado.")
            time.sleep(WaitTimes.VERY_SHORT_WAIT)
        except Exception:
            print("[DEBUG] No apareció 'Continuar sin voz' o ya fue manejado.")

    def _set_initial_listen_mode(self) -> None:
        """Establece el modo inicial de escuchar."""
        try:
            listen_btn = self.page.get_by_text(re.compile(r"Escuchar|Listen", re.I))
            listen_btn.first.click(timeout=3000)
            print("[DEBUG] Modo 'Escuchar' activado.")
            time.sleep(WaitTimes.VERY_SHORT_WAIT)
        except Exception:
            print("[DEBUG] No se pudo activar modo 'Escuchar' o ya estaba activo.")

    def _play_audio(self) -> None:
        """Reproduce el audio de la historia."""
        try:
            # Intentar reproducir con el botón polygon (reproducir)
            play_btn = self.page.locator("polygon").nth(3)
            play_btn.click(timeout=3000)
            print("[DEBUG] Audio iniciado (polygon).")
        except Exception:
            try:
                # Método alternativo para reproducir
                play_btn = self.page.locator("circle")
                play_btn.click(timeout=3000)
                print("[DEBUG] Audio iniciado (circle).")
            except Exception:
                print("[DEBUG] No se pudo iniciar el audio con los métodos conocidos.")

    def _alternate_read_listen(self) -> None:
        """Intercala entre los modos de leer y escuchar."""
        try:
            # Cambiar a modo "Leer"
            read_btn = self.page.get_by_text(re.compile(r"Leer|Read", re.I))
            read_btn.first.click(timeout=3000)
            print("[DEBUG] Cambiado a modo 'Leer'.")
            time.sleep(WaitTimes.VERY_SHORT_WAIT)

            # Volver a modo "Escuchar"
            listen_btn = self.page.get_by_text(re.compile(r"Escuchar|Listen", re.I))
            listen_btn.first.click(timeout=3000)
            print("[DEBUG] Cambiado a modo 'Escuchar'.")
            time.sleep(WaitTimes.VERY_SHORT_WAIT)

        except Exception as e:
            print(f"[DEBUG] Error intercalando modos leer/escuchar: {e}")

    def _check_story_completion(self) -> bool:
        """
        Verifica si la historia ha sido completada.

        Returns:
            bool: True si la historia está completa, False en caso contrario
        """
        try:
            # Buscar indicadores de finalización de historia
            # Esto puede variar según la interfaz de Rosetta Stone
            completion_indicators = [
                "Completado",
                "Completed",
                "Finalizado",
                "Finished",
            ]

            for indicator in completion_indicators:
                if self.page.get_by_text(indicator).count() > 0:
                    return True

            # Verificar si aparece botón de "Siguiente historia" o similar
            next_story_btn = self.page.get_by_text(re.compile(r"Siguiente|Next", re.I))
            if next_story_btn.count() > 0:
                return True

            return False

        except Exception:
            # Si hay error verificando, asumir que no está completa
            return False

    def checklist_on_histories(self) -> None:
        """
        Método legacy para compatibilidad. Redirige al nuevo método loop_all_histories.

        Esta función asume que el login y la navegación inicial hasta Foundations ya están completados.
        """
        print("[INFO] Método checklist_on_histories() ha sido refactorizado.")
        print("[INFO] Redirigiendo a loop_all_histories() para bucle infinito...")
        self.loop_all_histories()

    def _navigate_to_stories_section(self) -> bool:
        """Navega a la sección de Historias desde Foundations."""
        try:
            self.page.get_by_role("listitem").click()
            print("[DEBUG] Click en primer 'listitem' exitoso.")
        except Exception as e:
            print(f"[ERROR] No se pudo clicar 'listitem': {e}")
            return False

        try:
            self.page.get_by_text("Explorar todo el contenido").click()
            print("[DEBUG] Click en 'Explorar todo el contenido' exitoso.")
        except Exception as e:
            print(f"[ERROR] No se encontró 'Explorar todo el contenido': {e}")
            return False

        try:
            self.page.locator("a").nth(1).click()
            print("[DEBUG] Click en link de navegación exitoso.")
        except Exception as e:
            print(f"[ERROR] No se pudo clicar en link: {e}")
            return False

        # Esperamos a que cargue la sección
        time.sleep(WaitTimes.SHORT_WAIT)
        print(f"[DEBUG] URL en sección Historias: {self.page.url}")
        print(f"[DEBUG] Título de página: {self.page.title()}")
        return True

    def _return_to_stories_list(self) -> bool:
        """Regresa a la lista de historias."""
        try:
            self.page.locator("div").filter(
                has_text=re.compile(self.HISTORIAS_SELECTOR_PATTERN)
            ).click()
            print("[DEBUG] Regresando a Historias.")
            self.page.wait_for_load_state("networkidle")
            time.sleep(WaitTimes.SHORT_WAIT)
            return True
        except Exception:
            print("[ERROR] No se pudo regresar a la lista de Historias.")
            return False
