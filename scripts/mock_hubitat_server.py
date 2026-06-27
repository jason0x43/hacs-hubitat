#!/usr/bin/env python3

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

APP_ID = "123"
ACCESS_TOKEN = "token"

DEVICES = [
    {
        "id": "176",
        "name": "Generic Zigbee Outlet",
        "label": "Loft Fan",
    }
]

DEVICE_DETAILS = {
    "176": {
        "id": "176",
        "name": "Generic Zigbee Outlet",
        "label": "Loft Fan",
        "type": "Generic Zigbee Outlet",
        "room": "Loft",
        "capabilities": [
            "Switch",
            {"attributes": [{"name": "switch", "dataType": None}]},
            "Sensor",
        ],
        "attributes": [
            {
                "name": "switch",
                "currentValue": "off",
                "dataType": "ENUM",
                "values": ["on", "off"],
            }
        ],
        "commands": ["on", "off"],
    }
}

MODES = [
    {"id": "1", "name": "Day", "active": True},
    {"id": "2", "name": "Evening", "active": False},
]

HSM = {"hsm": "disarmed"}


class MockHubitatState:
    def __init__(self) -> None:
        self.lock = Lock()
        self.commands: list[dict[str, str | None]] = []
        self.post_urls: list[str] = []


class MockHubitatHandler(BaseHTTPRequestHandler):
    server: "MockHubitatServer"

    def do_GET(self) -> None:  # noqa: N802
        self.server.handle(self)

    def do_POST(self) -> None:  # noqa: N802
        self.server.handle(self)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"HTTP {self.address_string()} {format % args}", flush=True)


class MockHubitatServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, MockHubitatHandler)
        self.state = MockHubitatState()

    def handle(self, handler: MockHubitatHandler) -> None:
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        print(f"REQUEST {handler.command} {parsed.path}", flush=True)

        if params.get("access_token", [None])[0] != ACCESS_TOKEN:
            self._respond(handler, HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        prefix = f"/apps/api/{APP_ID}/"
        if not parsed.path.startswith(prefix):
            self._respond(handler, HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        api_path = parsed.path.removeprefix(prefix)
        parts = [part for part in api_path.split("/") if part]

        if api_path == "devices":
            self._respond(handler, HTTPStatus.OK, DEVICES)
            return

        if len(parts) >= 2 and parts[0] == "devices":
            self._handle_device(handler, parts)
            return

        if api_path == "modes":
            self._respond(handler, HTTPStatus.OK, MODES)
            return

        if len(parts) == 2 and parts[0] == "modes":
            self._set_mode(parts[1])
            self._respond(handler, HTTPStatus.OK, MODES)
            return

        if api_path == "hsm":
            self._respond(handler, HTTPStatus.OK, HSM)
            return

        if len(parts) == 2 and parts[0] == "hsm":
            HSM["hsm"] = parts[1]
            self._respond(handler, HTTPStatus.OK, HSM)
            return

        if api_path.startswith("postURL/"):
            post_url = unquote(api_path.removeprefix("postURL/"))
            with self.state.lock:
                self.state.post_urls.append(post_url)
            print(f"EVENT_URL {post_url}", flush=True)
            self._respond(handler, HTTPStatus.OK, {})
            return

        self._respond(handler, HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _handle_device(self, handler: MockHubitatHandler, parts: list[str]) -> None:
        device_id = parts[1]
        if len(parts) == 2:
            try:
                self._respond(handler, HTTPStatus.OK, DEVICE_DETAILS[device_id])
            except KeyError:
                self._respond(handler, HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        command = parts[2]
        argument = unquote(parts[3]) if len(parts) > 3 else None
        with self.state.lock:
            self.state.commands.append(
                {
                    "device_id": device_id,
                    "command": command,
                    "argument": argument,
                }
            )
        print(
            f"COMMAND device_id={device_id} command={command} argument={argument}",
            flush=True,
        )
        self._respond(handler, HTTPStatus.OK, {})

    def _set_mode(self, mode_id: str) -> None:
        for mode in MODES:
            mode["active"] = mode["id"] == mode_id

    def _respond(
        self,
        handler: MockHubitatHandler,
        status: HTTPStatus,
        payload: dict[str, Any] | list[dict[str, Any]],
    ) -> None:
        body = json.dumps(payload).encode()
        handler.send_response(status)
        handler.send_header("Content-Type", "text/html")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mock Hubitat Maker API server")
    parser.add_argument("--host", default="0.0.0.0", help="Listen host")
    parser.add_argument(
        "--port",
        type=int,
        default=80,
        help="Listen port for the mock Maker API",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = MockHubitatServer((args.host, args.port))
    print(f"Mock Hubitat listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
