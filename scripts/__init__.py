from subprocess import call, check_output

from hubitatmaker import __version__
from sys import exit
from shutil import copy as copyfile, rmtree
from os import chdir, environ
from os.path import join
from pathlib import Path
import toml


def init() -> None:
    call("poetry install", shell=True)
    call("poetry run pre-commit install", shell=True)


def test() -> None:
    call("pyright custom_components/hubitat", shell=True)
    call("poetry run pytest", shell=True)


def copy() -> None:
    if "HASS_CONFIG_PATH" not in environ:
        return
    dst = Path(environ["HASS_CONFIG_PATH"])
    src = Path(__file__).parent.parent
    chdir(src)

    print(f"Copying updated files to {dst}")

    files = (
        sorted(Path(".").glob("custom_components/**/*.py"))
        + sorted(Path(".").glob("custom_components/**/*.json"))
        + sorted(Path(".").glob("custom_components/**/*.yaml"))
    )

    for f in files:
        target = dst.joinpath(f)
        src_data = f.read_text()
        target_data = target.read_text()
        if src_data != target_data:
            copyfile(f, target)
            print(f"updated {f}")
