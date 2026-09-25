"""Run project checks from a temporary lock updated for current Home Assistant."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

from scripts.homeassistant_versions import latest_stable_homeassistant_version

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main(command: list[str], *, resolved: bool = False) -> int:
    """Run ``command`` with a temporary copy of the project's dependencies."""
    if not command:
        print("A command is required.", file=sys.stderr)
        return 2

    if resolved:
        print(f"Testing with Home Assistant {version('homeassistant')}", flush=True)
        return subprocess.run(command, check=False).returncode

    homeassistant_version = latest_stable_homeassistant_version()
    with tempfile.TemporaryDirectory(
        prefix="hubitat-current-homeassistant-"
    ) as temp_dir:
        temp_project = Path(temp_dir)
        for name in ("pyproject.toml", "uv.lock"):
            shutil.copy2(PROJECT_ROOT / name, temp_project / name)

        subprocess.run(
            [
                "uv",
                "add",
                "--project",
                str(temp_project),
                "--no-sync",
                "--upgrade-package",
                "pytest-homeassistant-custom-component",
                f"homeassistant=={homeassistant_version}",
            ],
            check=True,
        )
        return subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(temp_project),
                "--locked",
                "python",
                "-m",
                "scripts.run_with_current_homeassistant",
                "--resolved",
                *command,
            ],
            cwd=PROJECT_ROOT,
            check=False,
        ).returncode


if __name__ == "__main__":
    arguments = sys.argv[1:]
    is_resolved = bool(arguments and arguments[0] == "--resolved")
    raise SystemExit(
        main(arguments[1:] if is_resolved else arguments, resolved=is_resolved)
    )
