"""Hubitat API."""
from asyncio import gather
from logging import getLogger
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import quote

from aiohttp import ClientError, ClientResponse, ClientTimeout, request
from bs4 import BeautifulSoup
import voluptuous as vol

_LOGGER = getLogger(__name__)

Listener = Callable[[], None]

CAP_COLOR_CONTROL = "ColorControl"
CAP_COLOR_TEMP = "ColorTemperature"
CAP_SWITCH = "Switch"
CAP_SWITCH_LEVEL = "SwitchLevel"

ATTR_ACCELERATION = "acceleration"
ATTR_BATTERY = "battery"
ATTR_CONTACT = "contact"
ATTR_HUMIDITY = "humidity"
ATTR_ILLUMINANCE = "illuminance"
ATTR_MOTION = "motion"
ATTR_TEMPERATURE = "temperature"
ATTR_UV = "ultravioletIndex"

CMD_OFF = "off"
CMD_ON = "on"
CMD_SET_COLOR = "setColor"
CMD_SET_COLOR_TEMP = "setColorTemperature"
CMD_SET_HUE = "setHue"
CMD_SET_LEVEL = "setLevel"
CMD_SET_SAT = "setSaturation"

DEVICE_SCHEMA = vol.Schema({"id": str, "name": str, "label": str}, required=True)

DEVICES_SCHEMA = vol.Schema([DEVICE_SCHEMA])

ATTRIBUTE_SCHEMA = vol.Schema(
    {
        "name": str,
        "dataType": vol.Any(str, None),
        "currentValue": vol.Any(str, int, float, None),
        vol.Optional("values"): vol.Any([str], [int]),
    },
    required=True,
)

CAPABILITY_SCHEMA = vol.Schema(
    vol.Any(
        str,
        vol.Schema(
            {"attributes": [{"name": str, "dataType": vol.Any(str, None)}]},
            required=True,
        ),
    )
)

DEVICE_INFO_SCHEMA = vol.Schema(
    {
        "id": str,
        "name": str,
        "label": str,
        "attributes": [ATTRIBUTE_SCHEMA],
        "capabilities": [CAPABILITY_SCHEMA],
        "commands": [str],
    },
    required=True,
)

CAPABILITIES_SCHEMA = vol.Schema({"capabilities": [CAPABILITY_SCHEMA]}, required=True)

COMMAND_SCHEMA = vol.Schema({"command": str, "type": [str]}, required=True)

COMMANDS_SCHEMA = vol.Schema([COMMAND_SCHEMA])


class HubitatHub:
    """A representation of a Hubitat hub."""

    api: str
    app_id: str
    host: str
    token: str

    def __init__(self, host: str, app_id: str, access_token: str):
        """Initialize a Hubitat hub connector."""
        if not host:
            raise InvalidConfig('Missing "host"')
        if not app_id:
            raise InvalidConfig('Missing "app_id"')
        if not access_token:
            raise InvalidConfig('Missing "access_token"')

        self.host = host
        self.app_id = app_id
        self.token = access_token
        self.api = f"http://{host}/apps/api/{app_id}"

        self._devices: Dict[str, Dict[str, Any]] = {}
        self._info: Dict[str, str] = {}
        self._listeners: Dict[str, List[Listener]] = {}

        _LOGGER.debug(f"Created hub {self}")

    def __repr__(self):
        """Return a string representation of this hub."""
        return f"<HubitatHub host={self.host} app_id={self.app_id}>"

    @property
    def id(self):
        """Return the ID of this hub."""
        if len(self._info) > 0:
            return self._info["id"]
        return None

    @property
    def name(self):
        """Return the device name for hub."""
        return "Hubitat Elevation"

    @property
    def hw_version(self):
        """Return the hub's hardware version."""
        if len(self._info) > 0:
            return self._info["hw_version"]
        return None

    @property
    def sw_version(self):
        """Return the hub's software version."""
        if len(self._info) > 0:
            return self._info["sw_version"]
        return None

    @property
    def mac(self):
        """Return the MAC address of this hub."""
        if len(self._info) > 0:
            return self._info["mac"]
        return None

    @property
    def devices(self):
        """Return the devices managed by this hub."""
        if len(self._devices) > 0:
            return self._devices.values()
        return None

    def add_device_listener(self, device_id: str, listener: Listener):
        """Listen for updates for a device."""
        if device_id not in self._listeners:
            self._listeners[device_id] = []
        self._listeners[device_id].append(listener)

    def remove_device_listeners(self, device_id: str):
        """Remove all listeners for a device."""
        self._listeners[device_id] = []

    def device_has_attribute(self, device_id: str, attr: str):
        """Return True if the given device device has the given attribute."""
        try:
            self.get_device_attribute(device_id, attr)
            return True
        except Exception:
            return False

    async def check_config(self):
        """Verify that the hub is accessible."""
        try:
            await gather(self._load_info(), self._check_api())
        except ClientError as e:
            raise ConnectionError(str(e))

    async def connect(self):
        """
        Connect to the hub and download initial state data.

        Hub and device data will not be available until this method has
        completed
        """
        try:
            await gather(self._load_info(), self._load_devices())
            _LOGGER.debug(f"Connected to Hubitat hub at {self.host}")
        except ClientError as e:
            raise ConnectionError(str(e))

    def update_state(self, event: Dict[str, Any]):
        """Update a device state with an event received from the hub."""
        device_id = event["deviceId"]
        self._update_device_attr(device_id, event["name"], event["value"])
        if device_id in self._listeners:
            for listener in self._listeners[device_id]:
                listener()

    async def send_command(
        self, device_id: str, command: str, arg: Optional[Union[str, int]]
    ):
        """Send a device command to the hub."""
        path = f"devices/{device_id}/{command}"
        if arg:
            path += f"/{arg}"
        await self._api_request(path)

    def get_device_attribute(self, device_id: str, attr_name: str) -> Dict[str, Any]:
        """Get an attribute value for a specific device."""
        state = self._devices[device_id]
        for attr in state["attributes"]:
            if attr["name"] == attr_name:
                return attr
        raise InvalidAttribute(f"{device_id}.{attr_name}")

    async def set_event_url(self, event_url: str):
        """Set the URL that Hubitat will POST events to."""
        _LOGGER.info(f"Posting update to {self.api}/postURL/{event_url}")
        url = quote(event_url, safe="")
        await self._api_request(f"postURL/{url}")

    async def refresh_device(self, device_id: str):
        """Refresh a device's state."""
        await self._load_device(device_id, force_refresh=True)

    async def _check_api(self):
        """Check for api access."""
        await self._api_request("devices")

    def _update_device_attr(
        self, device_id: str, attr_name: str, value: Union[int, str]
    ):
        """Update a device attribute value."""
        _LOGGER.debug(f"Updating {attr_name} of {device_id} to {value}")
        state = self._devices[device_id]
        for attr in state["attributes"]:
            if attr["name"] == attr_name:
                attr["currentValue"] = value
                return
        raise InvalidAttribute

    async def _load_info(self):
        """Load general info about the hub."""
        url = f"http://{self.host}/hub/edit"
        _LOGGER.info(f"Getting hub info from {url}...")
        timeout = ClientTimeout(total=10)
        async with request("GET", url, timeout=timeout) as resp:
            if resp.status >= 400:
                raise RequestError(resp)

            text = await resp.text()
            try:
                soup = BeautifulSoup(text, "html.parser")
                section = soup.find("h2", string="Hub Details")
                self._info = _parse_details(section)
                _LOGGER.debug(f"Loaded hub info: {self._info}")
            except Exception as e:
                _LOGGER.error(f"Error parsing hub info: {e}")
                raise InvalidInfo()

    async def _load_devices(self, force_refresh=False):
        """Load the current state of all devices."""
        if force_refresh or len(self._devices) == 0:
            json = await self._api_request("devices")
            try:
                devices = DEVICES_SCHEMA(json)
                _LOGGER.debug(f"Loaded device list")
            except Exception as e:
                _LOGGER.error(f"Invalid response: {json}")
                raise e

            # load devices sequentially to avoid overloading the hub
            for dev in devices:
                await self._load_device(dev["id"], force_refresh)
                _LOGGER.debug(f"Loaded device {dev['id']}")

    async def _load_device(self, device_id: str, force_refresh=False):
        """
        Return full info for a specific device.

        {
            "id": "1922",
            "name": "Generic Z-Wave Smart Dimmer",
            "label": "Bedroom Light",
            "attributes": [
                {
                    "dataType": "NUMBER",
                    "currentValue": 10,
                    "name": "level"
                },
                {
                    "values": ["on", "off"],
                    "name": "switch",
                    "currentValue": "on",
                    "dataType": "ENUM"
                }
            ],
            "capabilities": [
                "Switch",
                {"attributes": [{"name": "switch", "currentValue": "off", "dataType": "ENUM", "values": ["on", "off"]}]},
                "Configuration",
                "SwitchLevel"
                {"attributes": [{"name": "level", "dataType": null}]}
            ],
            "commands": [
                "configure",
                "flash",
                "off",
                "on",
                "refresh",
                "setLevel"
            ]
        ]
        """

        if force_refresh or device_id not in self._devices:
            _LOGGER.debug(f"Loading device {device_id}")
            json = await self._api_request(f"devices/{device_id}")
            try:
                self._devices[device_id] = DEVICE_INFO_SCHEMA(json)
            except Exception as e:
                _LOGGER.error(f"Invalid device info: {json}")
                raise e
            _LOGGER.debug(f"Loaded device {device_id}")

    async def _api_request(self, path: str, method="GET"):
        params = {"access_token": self.token}
        async with request(method, f"{self.api}/{path}", params=params) as resp:
            if resp.status >= 400:
                if resp.status == 401:
                    raise InvalidToken()
                else:
                    raise RequestError(resp)
            json = await resp.json()
            if "error" in json and json["error"]:
                raise RequestError(resp)
            return json


_DETAILS_MAPPING = {
    "Hubitat Elevation® Platform Version": "sw_version",
    "Hardware Version": "hw_version",
    "Hub UID": "id",
    "IP Address": "address",
    "MAC Address": "mac",
}


def _parse_details(tag):
    """Parse hub details from HTML."""
    details: Dict[str, str] = {}
    group = tag.find_next_sibling("div")
    while group is not None:
        heading = group.find("div", class_="menu-header").text.strip()
        content = group.find("div", class_="menu-text").text.strip()
        if heading in _DETAILS_MAPPING:
            details[_DETAILS_MAPPING[heading]] = content
        group = group.find_next_sibling("div")
    return details


class ConnectionError(Exception):
    """Error when hub isn't responding."""


class InvalidToken(Exception):
    """Error for invalid access token."""


class InvalidConfig(Exception):
    """Error indicating invalid hub config data."""


class InvalidAttribute(Exception):
    """Error indicating an invalid device attribute."""


class InvalidInfo(Exception):
    """Error indicating that the hub returned invalid general info."""


class RequestError(Exception):
    """An error indicating that a request failed."""

    def __init__(self, resp: ClientResponse, **kwargs):
        """Initialize a request error."""
        super().__init__(
            f"{resp.method} {resp.url} - [{resp.status}] {resp.reason}", **kwargs,
        )
