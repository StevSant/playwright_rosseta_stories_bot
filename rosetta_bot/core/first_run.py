"""Interactive first-run setup: creates a .env file when one doesn't exist."""

import getpass
import os
from pathlib import Path

_MINIMAL_ENV_TEMPLATE = """\
# Rosetta Stone Bot Stories — Configuracion
# Generado automaticamente en la primera ejecucion.
# Puedes editar este archivo para cambiar la configuracion.

# === Credenciales ===
ROSETTA_EMAIL={email}
ROSETTA_PASSWORD={password}

# === Opciones avanzadas (descomenta para cambiar) ===
# Meta acumulada de horas de Stories entre todas las ejecuciones.
# TARGET_HOURS=35
#
# Modo de velocidad:
#   Por defecto el bot es RAPIDO: acredita TODAS las horas restantes hasta
#   TARGET_HOURS en una sola ejecucion, sin topes ni esperas.
#   Pon HUMAN_MODE=1 para acumular de forma gradual y humana (varias
#   ejecuciones al dia via el Programador de tareas). Solo entonces aplican
#   los limites de abajo.
# HUMAN_MODE=0
#
# --- Topes graduales (solo si HUMAN_MODE=1; ignorados en modo rapido) ---
# Horas acreditadas por ejecucion (rango aleatorio).
# SESSION_HOURS_MIN=0.5
# SESSION_HOURS_MAX=2.0
# Tope de horas por dia.
# MAX_HOURS_PER_DAY=2.5
"""


def _write_private(env_path: Path, content: str) -> None:
    """Write *content* to *env_path* with owner-only (0o600) permissions.

    The file holds the account password in plaintext, so it must not be
    world-readable. The mode is honored on POSIX; on Windows it is a no-op for
    ACLs, but writing this way keeps the credential file as locked-down as the
    platform allows.
    """
    fd = os.open(str(env_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(content)


def ensure_env_exists(env_path: Path) -> None:
    """If the env file doesn't exist, run interactive setup to create it."""
    if env_path.exists():
        return

    print("=" * 60)
    print("  Rosetta Stone Bot Stories")
    print("  Primera ejecucion — Configuracion inicial")
    print("=" * 60)
    print()

    email = input("Tu email de Rosetta Stone: ").strip()
    password = getpass.getpass("Tu contrasena (no se muestra al escribir): ").strip()

    if not email or not password:
        print("\nError: Email y contrasena son obligatorios.")
        raise SystemExit(1)

    _write_private(
        env_path, _MINIMAL_ENV_TEMPLATE.format(email=email, password=password)
    )

    print(f"\nArchivo .env creado en: {env_path}")
    print("Puedes editarlo despues para cambiar la configuracion.")
    print()
