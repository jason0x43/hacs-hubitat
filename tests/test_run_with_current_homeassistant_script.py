import importlib.util
from pathlib import Path
from typing import Any


def load_runner_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "run_with_current_homeassistant_script",
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_with_current_homeassistant.py",
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_main_runs_command_and_reports_homeassistant_version(
    capsys, monkeypatch
) -> None:
    module = load_runner_module()
    commands: list[tuple[list[str], bool]] = []

    class Result:
        returncode = 7

    monkeypatch.setattr(module, "version", lambda package: "2026.9.2")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda command, *, check: commands.append((command, check)) or Result(),
    )

    assert module.main(["pytest", "tests"]) == 7
    assert commands == [(["pytest", "tests"], False)]
    assert "Home Assistant 2026.9.2" in capsys.readouterr().out


def test_main_requires_command(capsys) -> None:
    module = load_runner_module()

    assert module.main([]) == 2
    assert "A command is required" in capsys.readouterr().err
