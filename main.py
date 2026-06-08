"""Entry point for the Lottery Number Generator desktop app.

Run with:

    python main.py

Requires only the Python standard library (Tkinter ships with CPython on
Windows and macOS; on Debian/Ubuntu install ``python3-tk``).
"""
from __future__ import annotations

import sys


def main() -> int:
    try:
        from ui import launch
    except ImportError as exc:  # pragma: no cover - environment dependent
        # Most commonly Tkinter is missing on a headless/Linux Python build.
        print(f"Failed to import the UI: {exc}", file=sys.stderr)
        print(
            "Tkinter is required. On Debian/Ubuntu: sudo apt install python3-tk",
            file=sys.stderr,
        )
        return 1

    launch()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
