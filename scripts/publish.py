#!/usr/bin/env python

import json
from subprocess import getoutput, check_call
from typing import cast

import tomlkit
from tomlkit.container import Container


def update_pyproject(new_version: str):
    with open("pyproject.toml") as f:
        pyproject = tomlkit.load(f)

    project = cast(Container, pyproject["project"])
    project["version"] = new_version

    with open("pyproject.toml", "w") as f:
        tomlkit.dump(pyproject, f)


def update_manifest(new_version: str):
    with open("custom_components/hubitat/manifest.json") as f:
        manifest = json.load(f)

    manifest["version"] = new_version

    with open("custom_components/hubitat/manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)


latest = getoutput("git describe --tags --abbrev=0")
version = latest[1:]
[major, minor, patch] = [int(x) for x in version.split(".")]
new_version = f"{major}.{minor}.{patch + 1}"

if input(f"Publish version {new_version} [y/N]? ") != "y":
    print("Aborting")
    exit(0)

update_pyproject(new_version)
update_manifest(new_version)

check_call('git commit --all -m "chore: update version number"', shell=True)
check_call(f"git tag v{new_version}", shell=True)
check_call("git push", shell=True)
check_call("git push --tags", shell=True)
