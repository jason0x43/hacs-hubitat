from collections.abc import AsyncIterator, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, cast
from unittest.mock import patch
from urllib.parse import unquote

import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import unused_port

from custom_components.hubitat.const import (
    H_CONF_APP_ID,
    H_CONF_HUB_ID,
    H_CONF_SERVER_PORT,
    H_CONF_SYNC_AREAS,
)
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load this custom integration in tests."""


class _FakeSocket:
    def connect(self, _address: tuple[str, int]) -> None:
        pass

    def getsockname(self) -> tuple[str, int]:
        return ("127.0.0.1", 0)

    def close(self) -> None:
        pass


@pytest.fixture(autouse=True)
def fake_hubitat_local_address_probe() -> Generator[None]:
    """Avoid DNS lookups for fake Hubitat hosts that include a test port."""

    @contextmanager
    def fake_open_socket(*_args: Any, **_kwargs: Any):
        yield _FakeSocket()

    with patch(
        "custom_components.hubitat.hubitatmaker.hub._open_socket",
        fake_open_socket,
    ):
        yield


@dataclass
class FakeHubitat:
    host: str
    app_id: str = "123"
    token: str = "token"
    hub_id: str = "hub12345"
    online: bool = True
    devices: list[dict[str, Any]] = field(default_factory=list)
    device_details: dict[str, dict[str, Any]] = field(default_factory=dict)
    modes: list[dict[str, Any]] = field(default_factory=list)
    hsm: dict[str, str] = field(default_factory=dict)
    requests: list[dict[str, Any]] = field(default_factory=list)
    post_urls: list[str] = field(default_factory=list)
    commands: list[dict[str, str | None]] = field(default_factory=list)
    event_server_port: int = 0

    @property
    def config_entry_data(self) -> dict[str, Any]:
        return {
            CONF_HOST: self.host,
            H_CONF_APP_ID: self.app_id,
            CONF_ACCESS_TOKEN: self.token,
            H_CONF_HUB_ID: self.hub_id,
        }

    @property
    def config_entry_options(self) -> dict[str, Any]:
        return {
            H_CONF_SERVER_PORT: self.event_server_port,
            H_CONF_SYNC_AREAS: True,
        }

    async def handle(self, request: web.Request) -> web.Response:
        self.requests.append(
            {
                "method": request.method,
                "path": request.path,
                "query": dict(request.query),
            }
        )

        if not self.online:
            transport = request.transport
            if transport is not None:
                transport.close()
            raise web.HTTPOk()

        if request.query.get("access_token") != self.token:
            raise web.HTTPUnauthorized()

        prefix = f"/apps/api/{self.app_id}/"
        if not request.path.startswith(prefix):
            raise web.HTTPNotFound()

        api_path = request.path.removeprefix(prefix)
        parts = api_path.split("/")

        if api_path == "devices":
            return web.json_response(self.devices, content_type="text/html")

        if len(parts) >= 2 and parts[0] == "devices":
            device_id = parts[1]
            if len(parts) == 2:
                return web.json_response(
                    self.device_details[device_id], content_type="text/html"
                )

            command = parts[2]
            argument = unquote(parts[3]) if len(parts) > 3 else None
            self.commands.append(
                {"device_id": device_id, "command": command, "argument": argument}
            )
            return web.json_response({}, content_type="text/html")

        if api_path == "modes":
            return web.json_response(self.modes, content_type="text/html")

        if len(parts) == 2 and parts[0] == "modes":
            mode_id = parts[1]
            for mode in self.modes:
                mode["active"] = mode["id"] == mode_id
            return web.json_response(self.modes, content_type="text/html")

        if api_path == "hsm":
            return web.json_response(self.hsm, content_type="text/html")

        if len(parts) == 2 and parts[0] == "hsm":
            self.hsm["hsm"] = parts[1]
            return web.json_response(self.hsm, content_type="text/html")

        if api_path.startswith("postURL/"):
            self.post_urls.append(unquote(api_path.removeprefix("postURL/")))
            return web.json_response({}, content_type="text/html")

        raise web.HTTPNotFound()


@pytest_asyncio.fixture
async def fake_hubitat(socket_enabled: None) -> AsyncIterator[FakeHubitat]:
    """Run a small local Maker API stand-in."""
    port = unused_port()
    fake = FakeHubitat(
        host=f"http://127.0.0.1:{port}",
        devices=[
            {
                "id": "176",
                "name": "Generic Zigbee Outlet",
                "label": "Loft Fan",
            },
            {
                "id": "6",
                "name": "Generic Z-Wave Contact Sensor",
                "label": "Office Door",
            },
        ],
        device_details={
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
            },
            "6": {
                "id": "6",
                "name": "Generic Z-Wave Contact Sensor",
                "label": "Office Door",
                "type": "Generic Z-Wave Contact Sensor",
                "room": "Office",
                "capabilities": [
                    "ContactSensor",
                    {"attributes": [{"name": "contact", "dataType": None}]},
                    "Sensor",
                ],
                "attributes": [
                    {
                        "name": "contact",
                        "currentValue": "closed",
                        "dataType": "ENUM",
                        "values": ["closed", "open"],
                    }
                ],
                "commands": [],
            },
        },
        modes=[
            {"id": "1", "name": "Day", "active": True},
            {"id": "2", "name": "Evening", "active": False},
        ],
        hsm={"hsm": "disarmed"},
    )

    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", fake.handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()

    try:
        yield fake
    finally:
        await runner.cleanup()


def get_state_entity_id(hass: Any, domain: str, name: str) -> str:
    for state in hass.states.async_all(domain):
        if cast(str, state.name) == name:
            return state.entity_id
    raise AssertionError(f"No {domain} entity named {name!r}")
