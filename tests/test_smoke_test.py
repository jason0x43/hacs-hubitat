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


def test_hubitat_warnings_filters_hubitat_warning_lines() -> None:
    smoke_test = load_smoke_test_module()

    warnings = smoke_test.hubitat_warnings(
        "\n".join(
            [
                (
                    "2026-08-10 WARNING (MainThread) "
                    "[custom_components.hubitat] First warning"
                ),
                (
                    "2026-08-10 ERROR (MainThread) "
                    "[custom_components.hubitat] Not a warning"
                ),
                "2026-08-10 WARNING (MainThread) [homeassistant.core] Not Hubitat",
                (
                    "2026-08-10 WARNING (MainThread) "
                    "[homeassistant.config_entries] Failed loading "
                    "custom_components.hubitat"
                ),
                (
                    "2026-08-10 WARNING (ImportExecutor_0) [homeassistant.const] "
                    "The deprecated constant CONCENTRATION_PARTS_PER_MILLION "
                    "was used from hubitat. Use UnitOfRatio.PARTS_PER_MILLION instead"
                ),
                (
                    "2026-08-10 WARNING (MainThread) [homeassistant.const] "
                    "The deprecated constant OTHER was used from another_integration"
                ),
                "2026-08-10 warning [CUSTOM_COMPONENTS.HUBITAT] Second warning",
            ]
        )
    )

    assert warnings == [
        ("2026-08-10 WARNING (MainThread) [custom_components.hubitat] First warning"),
        (
            "2026-08-10 WARNING (ImportExecutor_0) [homeassistant.const] "
            "The deprecated constant CONCENTRATION_PARTS_PER_MILLION "
            "was used from hubitat. Use UnitOfRatio.PARTS_PER_MILLION instead"
        ),
        "2026-08-10 warning [CUSTOM_COMPONENTS.HUBITAT] Second warning",
    ]


def test_wait_for_result_fails_for_hubitat_warnings(monkeypatch: Any) -> None:
    smoke_test = load_smoke_test_module()
    warning = "2026-08-10 WARNING (MainThread) [custom_components.hubitat] Warning"
    deprecation = (
        "2026-08-10 WARNING (ImportExecutor_0) [homeassistant.const] "
        "The deprecated constant CONCENTRATION_PARTS_PER_MILLION "
        "was used from hubitat. Use UnitOfRatio.PARTS_PER_MILLION instead"
    )

    monkeypatch.setattr(
        smoke_test,
        "docker_logs",
        lambda name: (
            f"{smoke_test.SUCCESS_MARKER}\n{warning}\n{deprecation}"
            if name == "home-assistant"
            else "\n".join(smoke_test.REQUIRED_MOCK_REQUESTS)
        ),
    )

    assert smoke_test.wait_for_result("home-assistant", "mock", timeout=1) == (
        False,
        "\n".join(
            [
                "Hubitat startup emitted warnings:",
                warning,
                deprecation,
            ]
        ),
        [warning, deprecation],
    )
