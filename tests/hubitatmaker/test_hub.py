import json
import re
from os.path import dirname, join
from typing import Any, final
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import unquote

import pytest

from custom_components.hubitat.hubitatmaker.const import (
    DeviceAttribute,
    HsmCommand,
)
from custom_components.hubitat.hubitatmaker.error import InvalidConfig
from custom_components.hubitat.hubitatmaker.hub import Hub
from custom_components.hubitat.hubitatmaker.types import Device

hub_edit_page: str = ""
devices: dict[str, Any] = {}
device_details: dict[str, Any] = {}
events: dict[str, dict[str, Any]] = {}
modes: list[dict[str, Any]] = []
hsm: dict[str, str] = {}
requests: list[dict[str, Any]] = []


def fake_get_mac_address(**_kwargs: str):
    return "aa:bb:cc:dd:ee:ff"


@final
class FakeResponse:
    def __init__(
        self,
        status: int = 200,
        data: str | dict[str, Any] | list[Any] = "",
        method: str = "GET",
        url: str = "/",
        reason: str = "",
    ):
        self.status = status
        self._data = data
        self.method = method
        self.url = url
        self.reason = reason

    async def json(self):
        if isinstance(self._data, str):
            return json.loads(self._data)
        return self._data

    async def text(self):
        if isinstance(self._data, str):
            return self._data
        return json.dumps(self._data)


default_responses = {}


def create_fake_request(responses: dict[str, Any] = default_responses):
    @final
    class FakeRequest:
        response: Any

        def __init__(self, method: str, url: str, **kwargs: dict[str, Any]):
            if url.endswith("/hub/edit"):
                if "/hub/edit" in responses.keys():
                    self.response = responses["/hub/edit"]
                else:
                    self.response = FakeResponse(data=hub_edit_page, url=url)
            elif url.endswith("/devices"):
                if "/devices" in responses.keys():
                    self.response = responses["/devices"]
                else:
                    self.response = FakeResponse(data=devices, url=url)
            elif url.endswith("/modes"):
                if "/modes" in responses.keys():
                    self.response = responses["/modes"]
                else:
                    self.response = FakeResponse(data=modes, url=url)
            elif url.endswith("/hsm"):
                if "/hsm" in responses.keys():
                    self.response = responses["/hsm"]
                else:
                    self.response = FakeResponse(data=hsm, url=url)
            else:
                mode_match = re.match(".*/modes/(\\d+)$", url)
                hsm_match = re.match(".*/hsm/(\\w+)$", url)
                dev_match = re.match(".*/devices/(\\d+)$", url)

                if mode_match:
                    mode_id = mode_match.group(1)
                    valid_mode = False
                    for mode in modes:
                        if mode["id"] == mode_id:
                            valid_mode = True
                            break
                    if valid_mode:
                        for mode in modes:
                            if mode["id"] == mode_id:
                                mode["active"] = True
                            else:
                                mode["active"] = False
                    self.response = FakeResponse(data=modes, url=url)
                elif hsm_match:
                    hsm_cmd = hsm_match.group(1)
                    new_mode = "disarmed"
                    if hsm_cmd == HsmCommand.DISARM:
                        new_mode = "disarmed"
                    self.response = FakeResponse(data={"hsm": new_mode}, url=url)
                elif dev_match:
                    dev_id: str = dev_match.group(1)
                    self.response = FakeResponse(
                        data=device_details.get(dev_id, {}), url=url
                    )
                else:
                    self.response = FakeResponse(data="{}", url=url)

            requests.append({"method": method, "url": url, "data": kwargs})

        async def __aenter__(self):
            return self.response

        async def __aexit__(self, exc_type: object, exc: object, tb: object):
            pass

    return FakeRequest


@pytest.fixture(autouse=True)
def before_each():
    global hub_edit_page
    global devices
    global device_details
    global events
    global modes
    global hsm
    global requests

    requests = []

    with open(join(dirname(__file__), "hub_edit.html")) as f:
        hub_edit_page = f.read()

    with open(join(dirname(__file__), "devices.json")) as f:
        devices = json.loads(f.read())

    with open(join(dirname(__file__), "device_details.json")) as f:
        device_details = json.loads(f.read())

    with open(join(dirname(__file__), "events.json")) as f:
        events = json.loads(f.read())

    with open(join(dirname(__file__), "modes.json")) as f:
        modes = json.loads(f.read())

    with open(join(dirname(__file__), "hsm.json")) as f:
        hsm = json.loads(f.read())


def test_hub_checks_arguments() -> None:
    """The hub should check for its required inputs."""
    pytest.raises(InvalidConfig, Hub, "", "1234", "token")
    pytest.raises(InvalidConfig, Hub, "1.2.3.4", "", "token")
    pytest.raises(InvalidConfig, Hub, "1.2.3.4", "1234", "")
    Hub("1.2.3.4", "1234", "token")


def test_initial_values() -> None:
    """Hub properties should have expected initial values."""
    hub = Hub("1.2.3.4", "1234", "token")
    assert list(hub.devices) == []


@pytest.mark.asyncio
async def test_hub_variables_are_loaded_written_and_updated_from_location_events() -> (
    None
):
    """Hub Variables retain their identities across writes and location events."""
    hub = Hub("1.2.3.4", "1234", "token")
    hub._api_request = mock.AsyncMock(  # type: ignore[method-assign]
        side_effect=[
            [
                {"name": "number with spaces", "type": "integer", "value": 1},
                {"name": "enabled", "type": "boolean", "value": True},
            ],
            {"name": "number with spaces", "type": "integer", "value": 2},
        ]
    )

    await hub.load_hub_variables()
    variable = hub.hub_variables["number with spaces"]
    listener = mock.Mock()
    hub.add_hub_variable_listener("number with spaces", listener)

    await hub.set_hub_variable("number with spaces", 2)
    assert hub.hub_variables["number with spaces"] is variable
    assert variable.value == 2
    hub._api_request.assert_awaited_with("hubvariables/number%20with%20spaces/2")

    boolean_event = {"deviceId": None, "name": "variable:enabled", "value": "false"}
    hub._process_event(boolean_event)
    assert hub.hub_variables["enabled"].value == "false"

    hub._process_event(
        {"deviceId": None, "name": "variable:number with spaces", "value": "3"}
    )
    listener.assert_called_once()
    assert variable.value == "3"


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_start_server(MockServer: mock.Mock) -> None:
    """Hub should start a server when asked to."""
    hub = Hub("1.2.3.4", "1234", "token", True)
    await hub.start()
    assert MockServer.called is True


@pytest.mark.parametrize(
    ("host", "expected_api_url"),
    [
        ("1.2.3.4", "http://1.2.3.4/apps/api/1234"),
        ("hub.example.com:8080", "http://hub.example.com:8080/apps/api/1234"),
        ("http://1.2.3.4", "http://1.2.3.4/apps/api/1234"),
        ("https://hub.example.com:8443", "https://hub.example.com:8443/apps/api/1234"),
    ],
)
def test_set_host(host: str, expected_api_url: str) -> None:
    """The hub address may include a scheme and/or a port."""
    hub = Hub(host, "1234", "token")
    assert hub.api_url == expected_api_url


@pytest.mark.parametrize(
    ("host", "expected_hostname"),
    [
        ("1.2.3.4", "1.2.3.4"),
        ("http://1.2.3.4", "1.2.3.4"),
        ("https://hub.example.com:8443", "hub.example.com"),
        ("hub.example.com:8080", "hub.example.com"),
    ],
)
@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_start_server_host_with_port(host: str, expected_hostname: str) -> None:
    """The event server address lookup should not include the hub's port."""
    sock = MagicMock()
    sock.getsockname.return_value = ("10.0.0.2", 12345)
    with patch(
        "custom_components.hubitat.hubitatmaker.hub._open_socket"
    ) as open_socket:
        open_socket.return_value.__enter__.return_value = sock
        hub = Hub(host, "1234", "token")
        await hub.start()
    sock.connect.assert_called_once_with((expected_hostname, 80))


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_start() -> None:
    """start() should request data from the Hubitat hub."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    # 14 requests:
    #   0: request devices
    #   1...: request device details
    #   -3: request modes
    #   -2: request hsm status
    #   -1: set event URL
    assert len(requests) == 14
    assert re.search("devices$", requests[0]["url"]) is not None
    assert re.search(r"devices/\d+$", requests[1]["url"]) is not None
    assert re.search(r"devices/\d+$", requests[2]["url"]) is not None
    assert re.search("modes$", requests[-3]["url"]) is not None
    assert re.search("hsm$", requests[-2]["url"]) is not None
    assert re.search("postURL", requests[-1]["url"]) is not None


@patch(
    "aiohttp.request",
    new=create_fake_request({"/hsm": FakeResponse(400, url="/hsm")}),
)
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_start_no_hsm() -> None:
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    assert hub.hsm_supported is False
    assert hub.mode_supported is True


@patch(
    "aiohttp.request",
    new=create_fake_request({"/modes": FakeResponse(400, url="/modes")}),
)
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_start_no_mode() -> None:
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    assert hub.hsm_supported is True
    assert hub.mode_supported is False


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_default_event_url(MockServer: mock.Mock) -> None:
    """Default event URL should be server URL."""
    MockServer.return_value.url = "http://127.0.0.1:81"
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    url = unquote(requests[-1]["url"])
    assert re.search(r"http://127.0.0.1:81$", url) is not None


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_custom_event_url(MockServer: mock.Mock) -> None:
    """Event URL should be configurable."""
    MockServer.return_value.url = "http://127.0.0.1:81"
    hub = Hub("1.2.3.4", "1234", "token", event_url="http://foo.local")
    await hub.start()
    url = unquote(requests[-1]["url"])
    assert re.search(r"http://foo\.local$", url) is not None


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_custom_event_url_without_port(MockServer: mock.Mock) -> None:
    """Event URL should use custom port if none was provided."""
    MockServer.return_value.url = "http://127.0.0.1:81"
    hub = Hub("1.2.3.4", "1234", "token", 420, event_url="http://foo.local")
    await hub.start()
    url = unquote(requests[-1]["url"])
    assert re.search(r"http://foo\.local:420$", url) is not None


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_custom_event_port(MockServer: mock.Mock) -> None:
    """Event server port should be configurable."""
    MockServer.return_value.url = "http://127.0.0.1:81"
    hub = Hub("1.2.3.4", "1234", "token", 420)
    await hub.start()
    assert MockServer.call_args[0][2] == 420


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_custom_event_port_from_url(MockServer: mock.Mock) -> None:
    """Event server port should come from event URL if none was provided."""
    MockServer.return_value.url = "http://127.0.0.1:81"
    hub = Hub("1.2.3.4", "1234", "token", event_url="http://foo.local:416")
    await hub.start()
    assert MockServer.call_args[0][2] == 416


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_custom_event_port_and_url(MockServer: mock.Mock) -> None:
    """Explicit event server port should override port from URL."""
    MockServer.return_value.url = "http://127.0.0.1:81"
    hub = Hub("1.2.3.4", "1234", "token", 420, "http://foo.local:416")
    await hub.start()
    assert MockServer.call_args[0][2] == 420


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_stop_server(MockServer: mock.Mock) -> None:
    """Hub should stop a server when stopped."""
    hub = Hub("1.2.3.4", "1234", "token", True)
    await hub.start()
    assert MockServer.return_value.start.called is True
    hub.stop()
    assert MockServer.return_value.stop.called is True


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_devices_loaded() -> None:
    """Started hub should have parsed device info."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    assert len(hub.devices) == 9


@pytest.mark.asyncio
async def test_failed_device_load_keeps_previous_complete_inventory() -> None:
    """A partial refresh must not replace the last complete device inventory."""
    hub = Hub("1.2.3.4", "1234", "token")
    previous_devices = {"existing": Device(device_details["6"])}
    hub._devices = previous_devices

    async def api_request(path: str) -> dict[str, Any] | list[dict[str, Any]]:
        if path == "devices":
            return [{"id": "6"}, {"id": "missing"}]
        if path == "devices/6":
            return device_details["6"]
        raise RuntimeError("device request failed")

    hub._api_request = AsyncMock(side_effect=api_request)  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="device request failed"):
        await hub.load_devices(force_refresh=True)

    assert hub._devices is previous_devices


@patch("aiohttp.request", new=create_fake_request())
@pytest.mark.asyncio
async def test_forced_device_load_preserves_instances_for_events() -> None:
    """Forced refreshes keep existing entity device references up to date."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.load_devices()
    device = hub.devices["176"]

    await hub.load_devices(force_refresh=True)

    assert hub.devices["176"] is device
    hub._process_event(events["device"])
    assert device.attributes[DeviceAttribute.SWITCH].value == "on"


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_process_event() -> None:
    """Started hub should process a device event."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    device = hub.devices["176"]
    attr = device.attributes[DeviceAttribute.SWITCH]
    assert attr.value == "off"

    hub._process_event(events["device"])

    attr = device.attributes[DeviceAttribute.SWITCH]
    assert attr.value == "on"


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_process_top_level_event() -> None:
    """Started hub should process an event without a content wrapper."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    device = hub.devices["176"]
    attr = device.attributes[DeviceAttribute.SWITCH]
    assert attr.value == "off"

    hub._process_event(events["device"]["content"])

    attr = device.attributes[DeviceAttribute.SWITCH]
    assert attr.value == "on"


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_process_mode_event() -> None:
    """Started hub should emit mode events."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()

    handler_called = False

    def listener(_: Any):
        nonlocal handler_called
        handler_called = True

    hub._process_event(events["mode"])
    assert handler_called is False

    hub.add_mode_listener(listener)
    hub._process_event(events["mode"])
    assert handler_called is True


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_process_top_level_mode_event() -> None:
    """Started hub should emit top-level mode events."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()

    handler_called = False

    def listener(_: Any):
        nonlocal handler_called
        handler_called = True

    hub.add_mode_listener(listener)
    hub._process_event(events["mode"]["content"])
    assert handler_called is True


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_process_hsm_event() -> None:
    """Started hub should emit HSM events."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()

    handler_called = False

    def listener(_: Any):
        nonlocal handler_called
        handler_called = True

    hub._process_event(events["hsmArmedAway"])
    assert handler_called is False

    hub.add_hsm_listener(listener)
    hub._process_event(events["hsmArmedAway"])
    assert handler_called is True


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_process_top_level_hsm_event() -> None:
    """Started hub should emit top-level HSM events."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()

    handler_called = False

    def listener(_: Any):
        nonlocal handler_called
        handler_called = True

    hub.add_hsm_listener(listener)
    hub._process_event(events["hsmArmedAway"]["content"])
    assert handler_called is True


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_process_other_event() -> None:
    """Started hub should ignore non-device, non-mode events."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    device = hub.devices["176"]
    attr = device.attributes[DeviceAttribute.SWITCH]
    assert attr.value == "off"

    hub._process_event(events["other"])

    attr = device.attributes[DeviceAttribute.SWITCH]
    assert attr.value == "off"


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_process_set_hsm() -> None:
    """Started hub should allow mode to be updated."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    assert hub.hsm_status == "armedAway"
    await hub.set_hsm(HsmCommand.DISARM)
    assert re.search(f"hsm/{HsmCommand.DISARM}$", requests[-1]["url"]) is not None

    hub._process_event(events["hsmAllDisarmed"])
    assert hub.hsm_status == "allDisarmed"


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_process_set_mode() -> None:
    """Started hub should allow mode to be updated."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    assert hub.mode == "Day"
    await hub.set_mode("Evening")
    assert re.search("modes/2$", requests[-1]["url"]) is not None

    hub._process_event(events["mode"])
    assert hub.mode == "Evening"


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_set_event_url(MockServer: mock.Mock) -> None:
    """Started hub should allow event URL to be set."""
    server_url = "http://127.0.0.1:81"
    MockServer.return_value.url = server_url
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()

    await hub.set_event_url(None)
    event_url = unquote(requests[-1]["url"])
    assert re.search(f"postURL/{server_url}$", event_url) is not None

    other_url = "http://10.0.1.1:4443"
    await hub.set_event_url(other_url)
    event_url = unquote(requests[-1]["url"])
    assert re.search(f"postURL/{other_url}$", event_url) is not None


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_set_port(MockServer: mock.Mock) -> None:
    """Started hub should allow port to be set."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    assert MockServer.call_args[0][2] == 0
    await hub.set_port(14)
    assert MockServer.call_args[0][2] == 14


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_hsm_is_supported() -> None:
    """hub should indicate if HSM is supported."""
    hub = Hub("1.2.3.4", "1234", "token")
    assert hub.hsm_supported is None
    await hub.start()
    assert hub.hsm_supported is True


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_mode_is_supported() -> None:
    """hub should indicate if HSM is supported."""
    hub = Hub("1.2.3.4", "1234", "token")
    assert hub.mode_supported is None
    await hub.start()
    assert hub.mode_supported is True


@pytest.mark.parametrize(
    ("host", "api_url"),
    [
        ("1.2.3.4", "http://1.2.3.4/apps/api/1234"),
        ("https://hub.local", "https://hub.local/apps/api/1234"),
        (
            "https://cloud.hubitat.com/api/abc-123/apps/1234",
            "https://cloud.hubitat.com/api/abc-123/apps/1234",
        ),
        (
            "https://cloud.hubitat.com/api/abc-123/apps/1234/",
            "https://cloud.hubitat.com/api/abc-123/apps/1234",
        ),
        (
            "https://cloud.hubitat.com/api/abc-123/apps/1234/devices?access_token=x",
            "https://cloud.hubitat.com/api/abc-123/apps/1234",
        ),
        (
            "https://cloud.hubitat.com/api/abc-123/apps",
            "https://cloud.hubitat.com/api/abc-123/apps/1234",
        ),
        (
            "https://cloud.hubitat.com/api/abc-123",
            "https://cloud.hubitat.com/api/abc-123/apps/1234",
        ),
        ("http://hub.local/apps/api/1234/devices", "http://hub.local/apps/api/1234"),
    ],
)
def test_set_host_api_url(host: str, api_url: str) -> None:
    """A host with a path is used as the Maker API base URL."""
    hub = Hub(host, "1234", "token")
    assert hub.api_url == api_url


@patch("aiohttp.request", new=create_fake_request())
@pytest.mark.asyncio
async def test_cloud_hub_requests_use_cloud_url() -> None:
    """Requests for a cloud hub go to the cloud API URL."""
    hub = Hub(
        "https://cloud.hubitat.com/api/abc-123/apps/1234",
        "1234",
        "token",
        start_server=False,
    )
    await hub.check_config()
    assert (
        requests[-1]["url"] == "https://cloud.hubitat.com/api/abc-123/apps/1234/devices"
    )


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_start_without_server(MockServer: mock.Mock) -> None:
    """A hub that doesn't use the server neither starts it nor sets a URL."""
    hub = Hub("1.2.3.4", "1234", "token", start_server=False)
    await hub.start()
    assert MockServer.called is False
    assert not any("postURL" in r["url"] for r in requests)

    await hub.set_port(14)
    assert MockServer.called is False


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_set_event_url_without_server(MockServer: mock.Mock) -> None:
    """An explicit event URL is sent even if no server is running."""
    hub = Hub("1.2.3.4", "1234", "token", start_server=False)
    await hub.start()

    await hub.set_event_url(None)
    assert not any("postURL" in r["url"] for r in requests)

    webhook_url = "http://10.0.1.2:8123/api/webhook/abc"
    await hub.set_event_url(webhook_url)
    event_url = unquote(requests[-1]["url"])
    assert re.search(f"postURL/{webhook_url}$", event_url) is not None


@patch("aiohttp.request", new=create_fake_request())
@pytest.mark.asyncio
async def test_process_event_public() -> None:
    """process_event handles events delivered from outside the server."""
    hub = Hub("1.2.3.4", "1234", "token", start_server=False)
    await hub.start()
    device = hub.devices["176"]
    assert device.attributes[DeviceAttribute.SWITCH].value == "off"

    hub.process_event(events["device"])

    assert device.attributes[DeviceAttribute.SWITCH].value == "on"
