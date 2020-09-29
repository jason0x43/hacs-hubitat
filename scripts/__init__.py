from subprocess import call, check_output

from hubitatmaker import __version__
from sys import exit
from shutil import rmtree
import toml


def init() -> None:
    call("poetry install", shell=True)
    call("poetry run pre-commit install", shell=True)


def test() -> None:
    call("poetry run mypy custom_components/hubitat", shell=True)
    call("poetry run pytest", shell=True)
