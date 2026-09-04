#!/usr/bin/env python3

"""Update the development dependencies that resolve Home Assistant."""

from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def update_homeassistant(project_dir: Path) -> None:
    """Upgrade Home Assistant through the project's development dependency group."""
    subprocess.run(
        [
            "uv",
            "lock",
            "--upgrade-group",
            "dev",
        ],
        cwd=project_dir,
        check=True,
    )


def main() -> int:
    """Update Home Assistant through the development dependency group."""
    update_homeassistant(PROJECT_ROOT)
    print("Updated the Home Assistant lockfile. Run: uv sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
