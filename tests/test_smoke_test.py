import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def load_smoke_test_module() -> Any:
    scripts_path = str(Path(__file__).resolve().parents[1] / "scripts")
    sys.path.insert(0, scripts_path)
    spec = importlib.util.spec_from_file_location(
        "smoke_test",
        Path(scripts_path) / "smoke_test.py",
    )
    assert spec is not None
    assert spec.loader is not None

    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts_path)


def test_create_config_writes_onboarded_storage(tmp_path: Path) -> None:
    smoke_test = load_smoke_test_module()

    smoke_test.create_config(tmp_path)

    storage = tmp_path / ".storage"
    onboarding = json.loads((storage / "onboarding").read_text())

    assert onboarding == {
        "version": 4,
        "key": "onboarding",
        "data": {"done": ["user", "core_config", "analytics", "integration"]},
    }
