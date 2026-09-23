# /// script
# requires-python = ">=3.14.2"
# dependencies = [
#   "homeassistant",
#   "poethepoet>=0.47.0",
#   "pytest",
#   "pytest-asyncio>=0.16.0",
#   "pytest-cov>=7.1.0",
#   "pytest-homeassistant-custom-component",
#   "ruff",
#   "setuptools>=62.2.0",
#   "tomlkit>=0.12.3",
#   "zuban>=0.7.0",
# ]
# ///

"""Run a command in an environment with the current Home Assistant release."""

from __future__ import annotations

import subprocess
import sys
from importlib.metadata import version


def main(command: list[str]) -> int:
    """Run ``command`` using the dependencies declared above."""
    if not command:
        print("A command is required.", file=sys.stderr)
        return 2

    print(f"Testing with Home Assistant {version('homeassistant')}", flush=True)
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
