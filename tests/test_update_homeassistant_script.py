import importlib.util
from pathlib import Path
from typing import Any


def load_update_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "update_homeassistant_script",
        Path(__file__).resolve().parents[1] / "scripts" / "update_homeassistant.py",
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_update_homeassistant_upgrades_development_group(monkeypatch, tmp_path) -> None:
    module = load_update_module()
    commands: list[tuple[list[str], Path, bool]] = []

    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda command, *, cwd, check: commands.append((command, cwd, check)),
    )

    module.update_homeassistant(tmp_path)

    assert commands == [
        (
            [
                "uv",
                "lock",
                "--upgrade-group",
                "dev",
            ],
            tmp_path,
            True,
        )
    ]


def test_main_updates_project_lockfile(capsys, monkeypatch, tmp_path) -> None:
    module = load_update_module()
    updated_projects: list[Path] = []

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        module,
        "update_homeassistant",
        lambda project_dir: updated_projects.append(project_dir),
    )

    assert module.main() == 0
    assert updated_projects == [tmp_path]
    assert "Run: uv sync" in capsys.readouterr().out
