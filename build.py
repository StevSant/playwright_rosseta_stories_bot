"""Build a single-file .exe with PyInstaller.

Usage:
    uv run --group dev python build.py

The .exe is written to dist/rosetta-bot-stories.exe. It reads its .env from the
folder the .exe sits in (or from a path passed as the first argument), and uses a
system-installed browser (Chrome/Edge), so the target machine does not need
`playwright install`.
"""

import PyInstaller.__main__

PyInstaller.__main__.run([
    "main.py",
    "--onefile",
    "--name=rosetta-bot-stories",
    "--console",
    "--clean",
    "--noconfirm",
    # Bundle the Playwright Python package + its node driver.
    "--collect-all=playwright",
])
