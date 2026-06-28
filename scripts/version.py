#!/usr/bin/env python

import argparse
import json
from typing import Any, cast

import tomlkit
from tomlkit.container import Container

PYPROJECT_PATH = "pyproject.toml"
MANIFEST_PATH = "custom_components/hubitat/manifest.json"
UV_LOCK_PATH = "uv.lock"
PACKAGE_NAME = "hubitat"


def read_pyproject_version() -> str:
    with open(PYPROJECT_PATH) as file:
        pyproject = tomlkit.load(file)

    project = cast(Container, pyproject["project"])
    return str(project["version"])


def update_pyproject(new_version: str) -> None:
    with open(PYPROJECT_PATH) as file:
        pyproject = tomlkit.load(file)

    project = cast(Container, pyproject["project"])
    if str(project["version"]) == new_version:
        return

    project["version"] = new_version

    with open(PYPROJECT_PATH, "w") as file:
        tomlkit.dump(pyproject, file)


def update_manifest(new_version: str) -> None:
    with open(MANIFEST_PATH) as file:
        manifest: dict[str, Any] = json.load(file)

    if manifest["version"] == new_version:
        return

    manifest["version"] = new_version

    with open(MANIFEST_PATH, "w") as file:
        json.dump(manifest, file, indent=2)
        file.write("\n")


def load_uv_lock_package() -> tuple[Any, Container]:
    with open(UV_LOCK_PATH) as file:
        lockfile = tomlkit.load(file)

    packages = cast(list[Container], lockfile["package"])
    for package in packages:
        if str(package["name"]) != PACKAGE_NAME:
            continue

        return lockfile, package

    raise ValueError(f'Package "{PACKAGE_NAME}" not found in {UV_LOCK_PATH}')


def update_uv_lock(new_version: str) -> None:
    lockfile, package = load_uv_lock_package()

    if str(package["version"]) == new_version:
        return

    package["version"] = new_version

    with open(UV_LOCK_PATH, "w") as file:
        tomlkit.dump(lockfile, file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Show or update the project version.")
    parser.add_argument(
        "version",
        nargs="?",
        help="Version to write to pyproject.toml, manifest.json, and uv.lock.",
    )
    args = parser.parse_args()

    if args.version is None:
        print(read_pyproject_version())
        return

    load_uv_lock_package()
    update_pyproject(args.version)
    update_manifest(args.version)
    update_uv_lock(args.version)
    print(args.version)


if __name__ == "__main__":
    main()
