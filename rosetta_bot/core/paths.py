"""
Filesystem path resolution that works both from source and a frozen .exe.

Under a PyInstaller one-file build, ``__file__`` points inside the temporary
``_MEIxxxxx`` extraction directory, which is wiped when the process exits.
Anything persistent (state files, saved login sessions, tracking data) must
therefore resolve against the .exe location instead of ``__file__``.
"""

import sys
from pathlib import Path


def app_base_dir() -> Path:
    """
    Base directory for persistent application files.

    Returns the directory next to the .exe when frozen, otherwise the
    project root (two levels above this package).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def sanitize_account_key(account_key: str) -> str:
    """Make an account identifier safe for use as a file name stem."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in account_key)


def auth_state_path(email: str) -> Path:
    """
    Path of the persisted Playwright ``storage_state`` (login session) file
    for *email*. Reusing it lets subsequent runs skip the login flow and
    avoids re-triggering Microsoft's new-device verification.
    """
    return app_base_dir() / "state" / f"auth_{sanitize_account_key(email)}.json"
