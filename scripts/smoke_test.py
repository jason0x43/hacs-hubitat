#!/usr/bin/env python3

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from homeassistant_versions import latest_stable_homeassistant_version

APP_ID = "123"
ACCESS_TOKEN = "token"
HUB_ID = "hub12345"
EVENT_PORT = 12345
MOCK_ALIAS = "hubitat-mock"

SUCCESS_MARKER = "Hubitat is ready"
FAILURE_MARKERS = (
    "Setup failed for custom integration 'hubitat'",
    "Error setting up entry hubitat",
    "Unable to import component: Exception importing custom_components.hubitat",
)
REQUIRED_MOCK_REQUESTS = (
    f"/apps/api/{APP_ID}/devices",
    f"/apps/api/{APP_ID}/devices/176",
    f"/apps/api/{APP_ID}/modes",
    f"/apps/api/{APP_ID}/hsm",
)


@dataclass
class SmokeResult:
    version: str
    success: bool
    message: str


class DockerResource:
    def __init__(self, kind: str, name: str) -> None:
        self.kind = kind
        self.name = name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run container-based Hubitat smoke tests against Home Assistant"
    )
    parser.add_argument(
        "--ha-version",
        dest="ha_versions",
        action="append",
        help=(
            "Home Assistant version to test (repeatable). Defaults to the latest "
            "stable release."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Seconds to wait after Home Assistant container startup begins",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep generated config directories after the run",
    )
    parser.add_argument(
        "--mock-image",
        default="python:3.13-slim",
        help="Container image used for the mock Hubitat server",
    )
    return parser.parse_args()


def run_command(
    *args: str, capture_output: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=True,
        text=True,
        capture_output=capture_output,
    )


def docker_logs(name: str) -> str:
    result = subprocess.run(
        ["docker", "logs", name],
        check=False,
        text=True,
        capture_output=True,
    )
    return (result.stdout or "") + (result.stderr or "")


def docker_state(name: str) -> tuple[str, int]:
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            "{{.State.Status}} {{.State.ExitCode}}",
            name,
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    output = (result.stdout or "").strip()
    if result.returncode != 0 or not output:
        return ("missing", -1)
    status, exit_code = output.split()
    return (status, int(exit_code))


def create_config(config_dir: Path) -> None:
    storage_dir = config_dir / ".storage"
    storage_dir.mkdir(parents=True, exist_ok=True)

    (config_dir / "configuration.yaml").write_text(
        "\n".join(
            [
                "logger:",
                "  default: info",
                "  logs:",
                "    custom_components.hubitat: debug",
                "",
            ]
        )
    )

    (storage_dir / "core.config").write_text(
        json.dumps(
            {
                "version": 1,
                "minor_version": 4,
                "key": "core.config",
                "data": {
                    "latitude": 53.5461,
                    "longitude": -113.4938,
                    "elevation": 645,
                    "unit_system_v2": "metric",
                    "location_name": "Smoke Test",
                    "time_zone": "America/Edmonton",
                    "external_url": None,
                    "internal_url": None,
                    "currency": "CAD",
                    "country": "CA",
                    "language": "en",
                    "unit_system": "metric",
                    "radius": 50,
                },
            }
        )
    )

    (storage_dir / "onboarding").write_text(
        json.dumps(
            {
                "version": 4,
                "key": "onboarding",
                "data": {"done": ["user", "core_config", "analytics", "integration"]},
            }
        )
    )

    entry: dict = {
        "created_at": "1970-01-01T00:00:00+00:00",
        "data": {
            "access_token": ACCESS_TOKEN,
            "app_id": APP_ID,
            "host": f"http://{MOCK_ALIAS}",
            "hub_id": HUB_ID,
        },
        "disabled_by": None,
        "discovery_keys": {},
        "domain": "hubitat",
        "entry_id": "hubitat-smoke-entry",
        "minor_version": 1,
        "modified_at": "1970-01-01T00:00:00+00:00",
        "options": {
            "access_token": ACCESS_TOKEN,
            "app_id": APP_ID,
            "device_type_overrides": {},
            "host": f"http://{MOCK_ALIAS}",
            "server_interface": None,
            "server_port": EVENT_PORT,
            "server_ssl_cert": None,
            "server_ssl_key": None,
            "server_url": None,
            "sync_areas": True,
            "temperature_unit": "C",
            "update_he_url": False,
        },
        "pref_disable_new_entities": False,
        "pref_disable_polling": False,
        "source": "user",
        "subentries": [],
        "title": "Hubitat",
        "unique_id": HUB_ID,
        "version": 2,
    }
    (storage_dir / "core.config_entries").write_text(
        json.dumps(
            {
                "version": 1,
                "minor_version": 5,
                "key": "core.config_entries",
                "data": {"entries": [entry]},
            }
        )
    )


def wait_for_result(ha_name: str, mock_name: str, timeout: int) -> tuple[bool, str]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ha_logs = docker_logs(ha_name)
        mock_logs = docker_logs(mock_name)
        if SUCCESS_MARKER in ha_logs and all(
            marker in mock_logs for marker in REQUIRED_MOCK_REQUESTS
        ):
            return True, "Hubitat loaded and contacted the mock Maker API"
        if any(marker in ha_logs for marker in FAILURE_MARKERS):
            return False, "Home Assistant reported a Hubitat setup failure"

        status, exit_code = docker_state(ha_name)
        if status == "exited":
            return False, f"Home Assistant container exited with code {exit_code}"

        time.sleep(2)

    return False, f"Timed out after {timeout}s waiting for Hubitat startup"


def run_smoke_test(
    repo_root: Path,
    version: str,
    timeout: int,
    mock_image: str,
    keep_temp: bool,
) -> SmokeResult:
    suffix = uuid4().hex[:8]
    network_name = f"hubitat-smoke-net-{suffix}"
    mock_name = f"hubitat-smoke-mock-{suffix}"
    ha_name = f"hubitat-smoke-ha-{suffix}"
    resources = [
        DockerResource("container", ha_name),
        DockerResource("container", mock_name),
        DockerResource("network", network_name),
    ]

    temp_dir = Path(
        tempfile.mkdtemp(prefix=f"hubitat-smoke-{version.replace('.', '-')}-")
    )
    config_dir = temp_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    create_config(config_dir)

    server_path = repo_root / "scripts" / "mock_hubitat_server.py"
    extension_path = repo_root / "custom_components" / "hubitat"

    try:
        print("🛠️ Creating test network...")
        run_command("docker", "network", "create", network_name)

        print("🚚 Starting mock Hubitat container...")
        run_command(
            "docker",
            "run",
            "--quiet",
            "-d",
            "--rm",
            "--name",
            mock_name,
            "--network",
            network_name,
            "--network-alias",
            MOCK_ALIAS,
            "-v",
            f"{server_path}:/app/mock_hubitat_server.py:ro",
            mock_image,
            "python",
            "/app/mock_hubitat_server.py",
            "--host",
            "0.0.0.0",
            "--port",
            "80",
        )

        print("🚚 Starting Home Assistant container...")
        run_command(
            "docker",
            "run",
            "--quiet",
            "-d",
            "--rm",
            "--name",
            ha_name,
            "--network",
            network_name,
            "-v",
            f"{config_dir}:/config",
            "-v",
            f"{extension_path}:/config/custom_components/hubitat:ro",
            "homeassistant/home-assistant:" + version,
        )

        success, message = wait_for_result(ha_name, mock_name, timeout)
        if success:
            return SmokeResult(version=version, success=True, message=message)

        ha_logs = docker_logs(ha_name)
        mock_logs = docker_logs(mock_name)
        return SmokeResult(
            version=version,
            success=False,
            message="\n".join(
                [
                    message,
                    "",
                    "Home Assistant logs:",
                    ha_logs.strip(),
                    "",
                    "Mock Hubitat logs:",
                    mock_logs.strip(),
                ]
            ).strip(),
        )
    finally:
        for resource in resources:
            if resource.kind == "container":
                subprocess.run(
                    ["docker", "rm", "-f", resource.name],
                    check=False,
                    capture_output=True,
                    text=True,
                )
            else:
                subprocess.run(
                    ["docker", "network", "rm", resource.name],
                    check=False,
                    capture_output=True,
                    text=True,
                )
        if not keep_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            print(f"Kept temp config at {temp_dir}")


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    results: list[SmokeResult] = []
    versions = args.ha_versions or [latest_stable_homeassistant_version()]

    for version in versions:
        print(f"Running Hubitat smoke test against Home Assistant {version}...")
        result = run_smoke_test(
            repo_root=repo_root,
            version=version,
            timeout=args.timeout,
            mock_image=args.mock_image,
            keep_temp=args.keep_temp,
        )
        results.append(result)
        if result.success:
            print(f"✅ {version}: {result.message}")
        else:
            print(f"❌ {version}: {result.message}", file=sys.stderr)

    return 0 if all(result.success for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
