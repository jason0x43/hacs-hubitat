"""Check whether Home Assistant is current under the project's constraints."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCKFILE_NAME = "uv.lock"
PYPROJECT_NAME = "pyproject.toml"
PACKAGE_NAME = "homeassistant"


def read_locked_package_version(lockfile_path: Path, package_name: str) -> str:
    """Return the locked version for one package from a uv lockfile."""
    with lockfile_path.open("rb") as lockfile:
        lockfile_data = tomllib.load(lockfile)

    for package in lockfile_data["package"]:
        if package["name"] == package_name:
            return str(package["version"])

    raise ValueError(f"Package {package_name!r} was not found in {lockfile_path}.")


def copy_resolution_inputs(project_dir: Path, temp_dir: Path) -> None:
    """Copy the files needed to resolve the project's dependency graph."""
    shutil.copy2(project_dir / PYPROJECT_NAME, temp_dir / PYPROJECT_NAME)
    shutil.copy2(project_dir / LOCKFILE_NAME, temp_dir / LOCKFILE_NAME)


def upgrade_lockfile(temp_dir: Path) -> None:
    """Resolve the newest dependency set allowed by the project's constraints."""
    subprocess.run(
        ["uv", "lock", "--upgrade"],
        cwd=temp_dir,
        check=True,
    )


def latest_compatible_package_version(
    project_dir: Path,
    package_name: str,
) -> str:
    """Return the newest lockable version for one package."""
    with tempfile.TemporaryDirectory(prefix="hubitat-homeassistant-check-") as temp_dir:
        temp_path = Path(temp_dir)
        copy_resolution_inputs(project_dir, temp_path)
        upgrade_lockfile(temp_path)
        return read_locked_package_version(temp_path / LOCKFILE_NAME, package_name)


def current_package_version(project_dir: Path, package_name: str) -> str:
    """Return the currently locked version for one package."""
    return read_locked_package_version(project_dir / LOCKFILE_NAME, package_name)


def main() -> int:
    """Run the Home Assistant freshness check for pre-commit."""
    current_version = current_package_version(PROJECT_ROOT, PACKAGE_NAME)
    latest_compatible_version = latest_compatible_package_version(
        PROJECT_ROOT, PACKAGE_NAME
    )

    print(f"Locked Home Assistant version: {current_version}")
    print(f"Latest compatible Home Assistant version: {latest_compatible_version}")

    if current_version != latest_compatible_version:
        print("Home Assistant is not at the newest compatible locked version.")
        print("Run: uv run poe update-homeassistant")
        return 1

    print("Home Assistant is current under the project's constraints.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
