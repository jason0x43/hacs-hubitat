import json
import re
from os.path import dirname, join
from typing import Any, Dict, List, Union
from unittest.mock import MagicMock, patch
from urllib.parse import unquote

import pytest

from custom_components.hubitat.hubitatmaker.const import HsmCommand
from custom_components.hubitat.hubitatmaker.hub import Hub, InvalidConfig

hub_edit_page: str = ""
devices: Dict[str, Any] = {}
device_details: Dict[str, Any] = {}
events: Dict[str, Dict[str, Any]] = {}
modes: List[Dict[str, Any]] = []
hsm: Dict[str, str] = {}
requests: List[Dict[str, Any]] = []


def fake_get_mac_address(**kwargs: str):
    return "aa:bb:cc:dd:ee:ff"


class FakeResponse:
    def __init__(
        self,
        status=200,
        data: Union[str, Dict, List] = "",
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


def create_fake_request(responses: Dict = {}):
    class FakeRequest:
        def __init__(self, method: str, url: str, **kwargs: Any):
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
                    dev_id = dev_match.group(1)
                    self.response = FakeResponse(
                        data=device_details.get(dev_id, {}), url=url
                    )
                else:
                    self.response = FakeResponse(data="{}", url=url)

            requests.append({"method": method, "url": url, "data": kwargs})

        async def __aenter__(self):
            return self.response

        async def __aexit__(self, exc_type, exc, tb):
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


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_start_server(MockServer) -> None:
    """Hub should start a server when asked to."""
    hub = Hub("1.2.3.4", "1234", "token", True)
    await hub.start()
    assert MockServer.called is True


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_start() -> None:
    """start() should request data from the Hubitat hub."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    # 13 requests:
    #   0: set event URL
    #   1: request devices
    #   2...: request device details
    #   -2: request modes
    #   -1: request hsm status
    assert len(requests) == 13
    assert re.search("devices$", requests[1]["url"]) is not None
    assert re.search(r"devices/\d+$", requests[2]["url"]) is not None
    assert re.search(r"devices/\d+$", requests[3]["url"]) is not None
    assert re.search("modes$", requests[-2]["url"]) is not None
    assert re.search("hsm$", requests[-1]["url"]) is not None


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
async def test_default_event_url(MockServer) -> None:
    """Default event URL should be server URL."""
    MockServer.return_value.url = "http://127.0.0.1:81"
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    url = unquote(requests[0]["url"])
    assert re.search(r"http://127.0.0.1:81$", url) is not None


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_custom_event_url(MockServer) -> None:
    """Event URL should be configurable."""
    MockServer.return_value.url = "http://127.0.0.1:81"
    hub = Hub("1.2.3.4", "1234", "token", event_url="http://foo.local")
    await hub.start()
    url = unquote(requests[0]["url"])
    assert re.search(r"http://foo\.local$", url) is not None


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_custom_event_url_without_port(MockServer) -> None:
    """Event URL should use custom port if none was provided."""
    MockServer.return_value.url = "http://127.0.0.1:81"
    hub = Hub("1.2.3.4", "1234", "token", 420, event_url="http://foo.local")
    await hub.start()
    url = unquote(requests[0]["url"])
    assert re.search(r"http://foo\.local:420$", url) is not None


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_custom_event_port(MockServer) -> None:
    """Event server port should be configurable."""
    MockServer.return_value.url = "http://127.0.0.1:81"
    hub = Hub("1.2.3.4", "1234", "token", 420)
    await hub.start()
    assert MockServer.call_args[0][2] == 420


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_custom_event_port_from_url(MockServer) -> None:
    """Event server port should come from event URL if none was provided."""
    MockServer.return_value.url = "http://127.0.0.1:81"
    hub = Hub("1.2.3.4", "1234", "token", event_url="http://foo.local:416")
    await hub.start()
    assert MockServer.call_args[0][2] == 416


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_custom_event_port_and_url(MockServer) -> None:
    """Explicit event server port should override port from URL."""
    MockServer.return_value.url = "http://127.0.0.1:81"
    hub = Hub("1.2.3.4", "1234", "token", 420, "http://foo.local:416")
    await hub.start()
    assert MockServer.call_args[0][2] == 420


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server")
@pytest.mark.asyncio
async def test_stop_server(MockServer) -> None:
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


@patch("aiohttp.request", new=create_fake_request())
@patch("custom_components.hubitat.hubitatmaker.server.Server", new=MagicMock())
@pytest.mark.asyncio
async def test_process_event() -> None:
    """Started hub should process a device event."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    device = hub.devices["176"]
    attr = device.attributes["switch"]
    assert attr.value == "off"

    hub._process_event(events["device"])

    attr = device.attributes["switch"]
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
async def test_process_other_event() -> None:
    """Started hub should ignore non-device, non-mode events."""
    hub = Hub("1.2.3.4", "1234", "token")
    await hub.start()
    device = hub.devices["176"]
    attr = device.attributes["switch"]
    assert attr.value == "off"

    hub._process_event(events["other"])

    attr = device.attributes["switch"]
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
async def test_set_event_url(MockServer) -> None:
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
async def test_set_port(MockServer) -> None:
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
