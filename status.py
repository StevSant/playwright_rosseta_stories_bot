#!/usr/bin/env python3
"""
CLI tool to check time tracking status for all users.

Usage:
    python -m rosetta_bot.cli.status
    python status.py
"""

from rosetta_bot.services import list_all_users


def main():
    """Display time tracking status for all users."""
    print("=" * 60)
    print("ROSETTA STONE BOT - ESTADO DE HORAS")
    print("=" * 60)
    print()

    users = list_all_users()

    if not users:
        print("No hay usuarios registrados todavía.")
        return

    print(
        f"{'Usuario':<35} {'Horas':>8} {'Progreso':>10} {'Sesiones':>10} {'Estado':>12}"
    )
    print("-" * 75)

    for user in users:
        email = user["email"]
        if len(email) > 33:
            email = email[:30] + "..."

        hours = f"{user['total_hours']:.1f}h"
        progress = f"{user['progress_percent']:.1f}%"
        sessions = str(user["sessions"])
        status = "✅ LISTO" if user["completed"] else "⏳ EN CURSO"

        print(f"{email:<35} {hours:>8} {progress:>10} {sessions:>10} {status:>12}")

    print("-" * 75)
    print(f"Total usuarios: {len(users)}")
    completed = sum(1 for u in users if u["completed"])
    print(f"Completados: {completed}/{len(users)}")
    print()

    # Show detailed info for incomplete users
    incomplete = [u for u in users if not u["completed"]]
    if incomplete:
        print("\nUsuarios pendientes:")
        for user in incomplete:
            remaining = user["target_hours"] - user["total_hours"]
            print(f"  • {user['email']}: faltan {remaining:.1f}h")


if __name__ == "__main__":
    main()
