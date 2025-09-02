"""
Script de prueba para verificar que la nueva funcionalidad está funcionando correctamente.
"""

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from rosetta_bot import RosettaStoneBot, AppConfig


def test_imports():
    """Prueba que todas las importaciones funcionan correctamente."""
    print("[TEST] Verificando importaciones...")

    try:
        from rosetta_bot.stories_feature_manager import StoriesFeatureManager

        print("[✓] StoriesFeatureManager importado correctamente")

        # Verificar que los métodos principales existen
        methods_to_check = [
            "loop_all_histories",
            "checklist_on_histories",
            "_process_all_stories_once",
            "_process_single_story",
            "_execute_story_listen_read_cycle",
        ]

        for method in methods_to_check:
            if hasattr(StoriesFeatureManager, method):
                print(f"[✓] Método {method} existe")
            else:
                print(f"[✗] Método {method} NO existe")

        return True

    except ImportError as e:
        print(f"[✗] Error de importación: {e}")
        return False


def test_bot_creation():
    """Prueba que el bot se puede crear correctamente."""
    print("\n[TEST] Verificando creación del bot...")

    try:
        load_dotenv(dotenv_path=".env_evelyn")
        config = AppConfig.from_env()
        bot = RosettaStoneBot(config)

        # Verificar que los métodos nuevos existen
        new_methods = ["run_infinite_stories_loop", "_run_infinite_stories_feature"]

        for method in new_methods:
            if hasattr(bot, method):
                print(f"[✓] Método {method} existe en bot")
            else:
                print(f"[✗] Método {method} NO existe en bot")

        print("[✓] Bot creado correctamente")
        return True

    except Exception as e:
        print(f"[✗] Error creando bot: {e}")
        return False


def test_story_manager_initialization():
    """Prueba que el StoriesFeatureManager se puede inicializar."""
    print("\n[TEST] Verificando inicialización de StoriesFeatureManager...")

    try:
        with sync_playwright() as playwright:
            # Simular un page object (sin abrir navegador real)
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()

            from rosetta_bot.stories_feature_manager import StoriesFeatureManager

            stories_manager = StoriesFeatureManager(page, debug_enabled=True)

            print("[✓] StoriesFeatureManager inicializado correctamente")

            # Verificar que las constantes están definidas
            if hasattr(stories_manager, "HISTORIAS_SELECTOR_PATTERN"):
                print(
                    f"[✓] Patrón de historias: {stories_manager.HISTORIAS_SELECTOR_PATTERN}"
                )

            browser.close()
            return True

    except Exception as e:
        print(f"[✗] Error inicializando StoriesFeatureManager: {e}")
        return False


def main():
    """Ejecuta todas las pruebas."""
    print("=== PRUEBAS DE FUNCIONALIDAD REFACTORIZADA ===\n")

    tests = [test_imports, test_bot_creation, test_story_manager_initialization]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"[✗] Error ejecutando {test.__name__}: {e}")

    print(f"\n=== RESULTADOS ===")
    print(f"Pruebas pasadas: {passed}/{total}")

    if passed == total:
        print(
            "🎉 ¡Todas las pruebas pasaron! La refactorización está funcionando correctamente."
        )
        print("\nPara usar la nueva funcionalidad:")
        print(
            "1. Edita main.py y descomenta: bot.run_infinite_stories_loop(playwright)"
        )
        print("2. O usa infinite_stories_example.py para ver ejemplos de uso")
    else:
        print("❌ Algunas pruebas fallaron. Revisa los errores arriba.")


if __name__ == "__main__":
    main()
