#!/usr/bin/env python

import argparse
import json
from typing import Any, cast

import tomlkit
from tomlkit.container import Container


def read_pyproject_version() -> str:
    with open("pyproject.toml") as file:
        pyproject = tomlkit.load(file)

    project = cast(Container, pyproject["project"])
    return str(project["version"])


def update_pyproject(new_version: str) -> None:
    with open("pyproject.toml") as file:
        pyproject = tomlkit.load(file)

    project = cast(Container, pyproject["project"])
    project["version"] = new_version

    with open("pyproject.toml", "w") as file:
        tomlkit.dump(pyproject, file)


def update_manifest(new_version: str) -> None:
    with open("custom_components/hubitat/manifest.json") as file:
        manifest: dict[str, Any] = json.load(file)

    if manifest["version"] == new_version:
        return

    manifest["version"] = new_version

    with open("custom_components/hubitat/manifest.json", "w") as file:
        json.dump(manifest, file, indent=2)
        file.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Show or update the project version.")
    parser.add_argument(
        "version",
        nargs="?",
        help="Version to write to pyproject.toml and manifest.json.",
    )
    args = parser.parse_args()

    if args.version is None:
        print(read_pyproject_version())
        return

    if read_pyproject_version() == args.version:
        print(args.version)
        return

    update_pyproject(args.version)
    update_manifest(args.version)
    print(args.version)


if __name__ == "__main__":
    main()
