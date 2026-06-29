import importlib.util
import json
from pathlib import Path
from typing import Any


def load_version_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "version_script",
        Path(__file__).resolve().parents[1] / "scripts" / "version.py",
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_update_uv_lock_updates_project_package_version(tmp_path) -> None:
    version_script = load_version_module()
    lockfile_path = tmp_path / "uv.lock"
    lockfile_path.write_text(
        """
version = 1
revision = 3
requires-python = ">=3.14.2"

[[package]]
name = "example"
version = "1.2.3"

[[package]]
name = "hubitat"
version = "0.10.5"
source = { virtual = "." }
""".lstrip()
    )

    original_path = version_script.UV_LOCK_PATH
    version_script.UV_LOCK_PATH = str(lockfile_path)
    try:
        version_script.update_uv_lock("0.10.6")
    finally:
        version_script.UV_LOCK_PATH = original_path

    assert 'name = "hubitat"\nversion = "0.10.6"' in lockfile_path.read_text()


def test_main_updates_lock_even_when_pyproject_version_already_matches(
    monkeypatch, tmp_path
) -> None:
    version_script = load_version_module()

    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """
[project]
name = "hubitat"
version = "0.10.6"
""".lstrip()
    )

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"version": "0.10.6"}) + "\n")

    lockfile_path = tmp_path / "uv.lock"
    lockfile_path.write_text(
        """
version = 1

[[package]]
name = "hubitat"
version = "0.10.5"
source = { virtual = "." }
""".lstrip()
    )

    monkeypatch.setattr(version_script, "PYPROJECT_PATH", str(pyproject_path))
    monkeypatch.setattr(version_script, "MANIFEST_PATH", str(manifest_path))
    monkeypatch.setattr(version_script, "UV_LOCK_PATH", str(lockfile_path))
    monkeypatch.setattr(version_script, "PACKAGE_NAME", "hubitat")
    monkeypatch.setattr("sys.argv", ["version.py", "0.10.6"])

    version_script.main()

    assert 'name = "hubitat"\nversion = "0.10.6"' in lockfile_path.read_text()
