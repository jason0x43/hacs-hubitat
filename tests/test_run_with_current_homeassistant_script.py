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


def test_main_updates_a_temporary_copy_of_the_project(monkeypatch, tmp_path) -> None:
    module = load_runner_module()
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname = 'hubitat'\n")
    (project / "uv.lock").write_text("original lock\n")
    commands: list[tuple[list[str], Path | None, bool]] = []
    copied_files: list[tuple[str, str]] = []

    class Result:
        returncode = 7

    monkeypatch.setattr(module, "PROJECT_ROOT", project)
    monkeypatch.setattr(
        module, "latest_stable_homeassistant_version", lambda: "2026.9.3"
    )

    def run(command: list[str], *, check: bool, cwd: Path | None = None) -> Result:
        temp_project = Path(command[command.index("--project") + 1])
        copied_files.append(
            (
                (temp_project / "pyproject.toml").read_text(),
                (temp_project / "uv.lock").read_text(),
            )
        )
        commands.append((command, cwd, check))
        return Result()

    monkeypatch.setattr(module.subprocess, "run", run)

    assert module.main(["pytest", "tests"]) == 7
    assert copied_files == [
        ("[project]\nname = 'hubitat'\n", "original lock\n"),
        ("[project]\nname = 'hubitat'\n", "original lock\n"),
    ]
    assert commands[0][0][0:2] == ["uv", "add"]
    assert commands[0][0][-3:] == [
        "--upgrade-package",
        "pytest-homeassistant-custom-component",
        "homeassistant==2026.9.3",
    ]
    assert commands[0][1:] == (None, True)
    assert commands[1][0][0:2] == ["uv", "run"]
    assert commands[1][0][-3:] == ["--resolved", "pytest", "tests"]
    assert commands[1][1:] == (project, False)
    assert (project / "uv.lock").read_text() == "original lock\n"


def test_resolved_main_reports_homeassistant_version_and_exit_code(
    capsys, monkeypatch
) -> None:
    module = load_runner_module()

    class Result:
        returncode = 7

    monkeypatch.setattr(module, "version", lambda package: "2026.9.2")
    monkeypatch.setattr(module.subprocess, "run", lambda command, *, check: Result())

    assert module.main(["pytest", "tests"], resolved=True) == 7
    assert "Home Assistant 2026.9.2" in capsys.readouterr().out


def test_main_requires_command(capsys) -> None:
    module = load_runner_module()

    assert module.main([]) == 2
    assert "A command is required" in capsys.readouterr().err
