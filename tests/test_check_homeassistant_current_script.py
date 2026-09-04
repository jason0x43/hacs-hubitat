import importlib.util
from pathlib import Path
from typing import Any


def load_check_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "check_homeassistant_current_script",
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "check_homeassistant_current.py",
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_lockfile(lockfile_path: Path, homeassistant_version: str) -> None:
    lockfile_path.write_text(
        f"""
version = 1

[[package]]
name = "homeassistant"
version = "{homeassistant_version}"
source = {{ registry = "https://pypi.org/simple" }}
""".lstrip()
    )


def test_read_locked_package_version_reads_homeassistant_version(tmp_path) -> None:
    module = load_check_module()
    lockfile_path = tmp_path / "uv.lock"
    write_lockfile(lockfile_path, "2026.6.4")

    version = module.read_locked_package_version(lockfile_path, "homeassistant")

    assert version == "2026.6.4"


def test_main_succeeds_when_locked_version_is_latest_compatible(
    capsys, monkeypatch, tmp_path
) -> None:
    module = load_check_module()
    write_lockfile(tmp_path / "uv.lock", "2026.6.4")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'hubitat'\n")

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        module,
        "latest_compatible_package_version",
        lambda project_dir, package_name: "2026.6.4",
    )

    result = module.main()

    captured = capsys.readouterr()
    assert result == 0
    assert "Home Assistant is current" in captured.out


def test_main_fails_when_newer_compatible_version_is_available(
    capsys, monkeypatch, tmp_path
) -> None:
    module = load_check_module()
    write_lockfile(tmp_path / "uv.lock", "2026.6.4")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'hubitat'\n")

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        module,
        "latest_compatible_package_version",
        lambda project_dir, package_name: "2026.7.0",
    )

    result = module.main()

    captured = capsys.readouterr()
    assert result == 1
    assert "Run: uv run poe update-homeassistant" in captured.out
