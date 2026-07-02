import sys
import types
from pathlib import Path
from typing import Any


def load_home_assistant_module() -> Any:
    script_path = Path(__file__).resolve().parents[1] / "home_assistant"
    module = types.ModuleType("home_assistant_script")
    module.__file__ = str(script_path)
    exec(compile(script_path.read_text(), str(script_path), "exec"), module.__dict__)
    return module


def test_parse_args_allows_start_without_explicit_version(monkeypatch) -> None:
    module = load_home_assistant_module()

    monkeypatch.setattr(sys, "argv", ["home_assistant", "start"])

    args = module.parse_args()

    assert args.command == "start"
    assert args.version is None


def test_cmd_start_uses_latest_stable_version_when_none_is_provided(
    monkeypatch, tmp_path
) -> None:
    module = load_home_assistant_module()
    commands: list[list[str]] = []

    monkeypatch.setattr(
        module,
        "latest_stable_homeassistant_version",
        lambda: "2026.6.4",
    )
    monkeypatch.setattr(module, "get_scriptdir", lambda: tmp_path)
    monkeypatch.setattr(module, "get_config_path", lambda: tmp_path / "config")
    monkeypatch.setattr(module, "getoutput", lambda _: "")
    monkeypatch.setattr(module, "call", lambda cmd: commands.append(cmd) or 0)

    (tmp_path / "config").mkdir()
    (tmp_path / "custom_components" / "hubitat").mkdir(parents=True)

    args = module.argparse.Namespace(version=None)

    module.cmd_start(args)

    assert commands == [
        [
            "docker",
            "run",
            "--rm",
            "--name",
            "homeassistant-2026.6.4",
            "-v",
            "/etc/localtime:/etc/localtime:ro",
            "-v",
            f"{tmp_path / 'config'}:/config",
            "-v",
            (
                f"{tmp_path / 'custom_components' / 'hubitat'}:"
                "/config/custom_components/hubitat"
            ),
            "-p",
            "8123:8123",
            "-p",
            "21064:21064",
            "-p",
            "12345:12345",
            "-p",
            "12346:12346",
            "homeassistant/home-assistant:2026.6.4",
        ]
    ]
