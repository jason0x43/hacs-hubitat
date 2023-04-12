"""Hubitat API."""
import asyncio
import socket
from contextlib import contextmanager
from logging import getLogger
from ssl import SSLContext
from types import MappingProxyType
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Union
from urllib.parse import ParseResult, quote, urlparse

import aiohttp
from aiohttp.client_exceptions import (
    ClientConnectionError,
    ContentTypeError,
)

from . import server
from .const import ID_HSM_STATUS, ID_MODE
from .error import InvalidConfig, InvalidMode, InvalidToken, RequestError
from .types import Device, Event, Mode

Listener = Callable[[Event], None]

MAX_REQUEST_ATTEMPT_COUNT = 3
REQUEST_RETRY_DELAY_INTERVAL = 0.5

_LOGGER = getLogger(__name__)


class Hub:
    """A representation of a Hubitat hub.

    This class downloads initial device data from a Hubitat hub and waits for
    the hub to push it state updates for devices.
    """

    api_url: str
    app_id: str
    host: str
    scheme: str
    token: str
    mac: str

    _server: server.Server

    def __init__(
        self,
        host: str,
        app_id: str,
        access_token: str,
        port: Optional[int] = None,
        event_url: Optional[str] = None,
        ssl_context: Optional[SSLContext] = None,
    ):
        """Initialize a Hubitat hub interface.

        host:
          The URL of the host to connect to (e.g., http://10.0.1.99), or just
          the host name/address. If only a name or address are provided, http
          is assumed.
        app_id:
          The ID of the Maker API instance this interface should use
        access_token:
          The access token for the Maker API instance
        port:
          The port to listen on for events (optional). Defaults to a random open port.
        event_url:
          The URL that Hubitat should send events to (optional). Defaults the server's
          actual address and port.
        ssl_context:
          The SSLContext the event listener server will use. Passing in a SSLContext
          object will make the event listener server HTTPS only.
        """
        if not host or not app_id or not access_token:
            raise InvalidConfig()

        self._devices: Dict[str, Device] = {}
        self._listeners: Dict[str, List[Listener]] = {}
        self._modes: List[Mode] = []
        self._mode_supported = None
        self._hsm_status: Optional[str] = None
        self._hsm_supported = None

        self.event_url = _get_event_url(port, event_url)
        self.port = _get_event_port(port, event_url)
        self.app_id = app_id
        self.token = access_token
        self.mac = ""
        self.ssl_context = ssl_context

        self.set_host(host)

        _LOGGER.info("Created hub %s", self)

    def __repr__(self) -> str:
        """Return a string representation of this hub."""
        return f"<Hub host={self.host} app_id={self.app_id}>"

    @property
    def devices(self) -> Mapping[str, Device]:
        """Return a list of devices managed by the Hubitat hub."""
        return MappingProxyType(self._devices)

    @property
    def mode(self) -> Optional[str]:
        """Return the current hub mode."""
        for mode in self._modes:
            if mode.active:
                return mode.name
        return None

    @property
    def mode_supported(self) -> Optional[bool]:
        return self._mode_supported

    @property
    def modes(self) -> List[str]:
        """Return the available hub modes."""
        return [m.name for m in self._modes]

    @property
    def hsm_status(self) -> Optional[str]:
        return self._hsm_status

    @property
    def hsm_supported(self) -> Optional[bool]:
        return self._hsm_supported

    def add_device_listener(self, device_id: str, listener: Listener) -> None:
        """Listen for updates for a particular device."""
        if device_id not in self._listeners:
            self._listeners[device_id] = []
        self._listeners[device_id].append(listener)

    def add_mode_listener(self, listener: Listener) -> None:
        """Listen for updates for the hub mode."""
        if ID_MODE not in self._listeners:
            self._listeners[ID_MODE] = []
        self._listeners[ID_MODE].append(listener)

    def add_hsm_listener(self, listener: Listener) -> None:
        """Listen for updates for the hub HSM status."""
        if ID_HSM_STATUS not in self._listeners:
            self._listeners[ID_HSM_STATUS] = []
        self._listeners[ID_HSM_STATUS].append(listener)

    def remove_device_listeners(self, device_id: str) -> None:
        """Remove all listeners for a particular device."""
        self._listeners[device_id] = []

    def remove_mode_listeners(self) -> None:
        """Remove all listeners for mode changes."""
        self._listeners[ID_MODE] = []

    def remove_hsm_status_listeners(self) -> None:
        """Remove all listeners for HSM status changes."""
        self._listeners[ID_HSM_STATUS] = []

    async def check_config(self) -> None:
        """Verify that the hub is accessible.

        This method will raise a ConnectionError if there was a problem
        communicating with the hub.
        """
        try:
            await self._check_api()
        except aiohttp.ClientError as e:
            raise ConnectionError(str(e))

    async def load_devices(self, force_refresh=False) -> None:
        """Load the current state of all devices."""
        if force_refresh or len(self._devices) == 0:
            devices: List[Dict[str, Any]] = await self._api_request("devices")
            _LOGGER.debug("Loaded device list")

            # load devices sequentially to avoid overloading the hub
            for dev in devices:
                await self._load_device(dev["id"], force_refresh)

    async def start(self) -> None:
        """Download initial state data, and start an event server if requested.

        Hub and device data will not be available until this method has
        completed. Methods that rely on that data will raise an error if called
        before this method has completed.
        """

        self._mode_supported = None
        self._hsm_supported = None

        try:
            await self._start_server()
            await self.load_devices()
            _LOGGER.debug("Connected to Hubitat hub at %s", self.host)
        except aiohttp.ClientError as e:
            raise ConnectionError(str(e))

        try:
            await self._load_modes()
            self._mode_supported = True
        except Exception as e:
            self._mode_supported = False
            _LOGGER.warning(f"Unable to access modes: {e}")

        try:
            await self._load_hsm_status()
            self._hsm_supported = True
        except Exception as e:
            self._hsm_supported = False
            _LOGGER.warning(f"Unable to access HSM status: {e}")

    def stop(self) -> None:
        """Remove all listeners and stop the event server (if running)."""
        if self._server:
            self._server.stop()
            _LOGGER.info("Stopped event server")
        self._listeners = {}

    async def refresh_device(self, device_id: str) -> None:
        """Refresh a device's state."""
        await self._load_device(device_id, force_refresh=True)

    async def send_command(
        self, device_id: str, command: str, arg: Optional[Union[str, int]]
    ) -> Dict[str, Any]:
        """Send a device command to the hub."""
        path = f"devices/{device_id}/{command}"
        if arg:
            path += f"/{arg}"
        _LOGGER.debug("Sending command %s(%s) to %s", command, arg, device_id)
        return await self._api_request(path)

    async def set_event_url(self, event_url: Optional[str]) -> None:
        """Set the URL that Hubitat will POST device events to."""
        if not event_url:
            event_url = self._server.url
        url = quote(str(event_url), safe="")
        _LOGGER.info("Setting event update URL to %s", url)
        await self._api_request(f"postURL/{url}")

    async def set_hsm(self, hsm_mode: str) -> None:
        """Update the hub's HSM status.

        hsm_mode must be one of the HSM_* constants.
        """
        new_mode: Dict[str, str] = await self._api_request(f"hsm/{hsm_mode}")
        self._hsm_status = new_mode["hsm"]

    async def set_mode(self, name: str) -> None:
        """Update the hub's mode"""
        id = None
        for mode in self._modes:
            if mode.name == name:
                id = mode.id
                break
        if id is None:
            _LOGGER.error("Invalid mode: %s", name)
            raise InvalidMode(name)

        new_modes: List[Dict[str, Any]] = await self._api_request(f"modes/{id}")
        self._modes = [Mode(m) for m in new_modes]

    def set_host(self, host: str) -> None:
        """Set the host address that the hub is accessible at."""
        _LOGGER.debug("Setting host to %s", host)
        host_url = urlparse(host)
        self.scheme = host_url.scheme or "http"
        self.host = host_url.netloc or host_url.path
        self.base_url = f"{self.scheme}://{self.host}"
        self.api_url = f"{self.base_url}/apps/api/{self.app_id}"

    async def set_port(self, port: int) -> None:
        """Set the port that the event listener server will listen on.

        Setting this will stop and restart the event listener server.
        """
        self.port = port
        _LOGGER.info("Setting port to %s", port)
        if self._server:
            self._server.stop()
        await self._start_server()

    async def set_ssl_context(self, ssl_context: Optional[SSLContext]) -> None:
        """Set the SSLContext that the event listener server will use. Passing in a
        SSLContext object will make the event listener server HTTPS only. Passing in
        None will revert the server back to HTTP.

        Setting this will stop and restart the event listener server.
        """
        self.ssl_context = ssl_context

        if ssl_context is None:
            _LOGGER.debug("Disabling SSL for event listener server")
        else:
            _LOGGER.debug("Enabling SSL for event listener server")

        if self._server:
            self._server.stop()
        await self._start_server()

    async def _check_api(self) -> None:
        """Check for api access.

        An error will be raised if a test API request fails.
        """
        await self._api_request("devices")

    def _process_event(self, event: Dict[str, Any]) -> None:
        """Process an event received from the hub."""
        try:
            content = event["content"]
            _LOGGER.debug("Received event: %s", content)
        except KeyError:
            _LOGGER.warning("Received invalid event: %s", event)
            return

        if content["deviceId"] is not None:
            device_id = content["deviceId"]
            self._update_device_attr(
                device_id, content["name"], content["value"], content["unit"]
            )

            evt = Event(content)

            if device_id in self._listeners:
                for listener in self._listeners[device_id]:
                    listener(evt)
        elif content["name"] == "mode":
            name = content["value"]
            mode_set = False
            for mode in self._modes:
                if mode.name == name:
                    mode.active = True
                    mode_set = True
                else:
                    mode.active = False

            # If the mode wasn't set, this is a new mode. Add a placeholder
            # to the modes list, and reload the modes
            if not mode_set:
                self._modes.append(Mode({"active": True, "name": name}))
                _ = self._load_modes()

            evt = Event(content)

            for listener in self._listeners.get(ID_MODE, []):
                listener(evt)

        elif content["name"] == "hsmStatus":
            self._hsm_status = content["value"]
            evt = Event(content)
            for listener in self._listeners.get(ID_HSM_STATUS, []):
                listener(evt)

    def _update_device_attr(
        self, device_id: str, attr_name: str, value: Union[int, str], value_unit: str
    ) -> None:
        """Update a device attribute value."""
        _LOGGER.debug(
            "Updating %s of %s to %s (%s)", attr_name, device_id, value, value_unit
        )
        try:
            dev = self._devices[device_id]
        except KeyError:
            _LOGGER.warning("Tried to update unknown device %s", device_id)
            return

        try:
            dev.update_attr(attr_name, value, value_unit)
        except KeyError:
            _LOGGER.warning("Tried to update unknown attribute %s", attr_name)

    async def _load_device(self, device_id: str, force_refresh=False) -> None:
        """Return full info for a specific device."""
        if force_refresh or device_id not in self._devices:
            _LOGGER.debug("Loading device %s", device_id)
            json = await self._api_request(f"devices/{device_id}")
            try:
                if device_id in self._devices:
                    self._devices[device_id].update_state(json)
                else:
                    self._devices[device_id] = Device(json)
            except Exception as e:
                _LOGGER.error("Invalid device info: %s", json)
                raise e
            _LOGGER.debug("Loaded device %s", device_id)

    async def _load_hsm_status(self) -> None:
        """Load the current hub HSM status."""
        hsm: Dict[str, str] = await self._api_request("hsm")
        _LOGGER.debug("Loaded hsm status")
        self._hsm_status = hsm["hsm"]

    async def _load_modes(self) -> None:
        """Load the current hub mode."""
        modes: List[Dict[str, Any]] = await self._api_request("modes")
        _LOGGER.debug("Loaded modes")
        self._modes = [Mode(m) for m in modes]

    async def _api_request(self, path: str, method="GET") -> Any:
        """Make a Maker API request."""
        params = {"access_token": self.token}

        attempt = 0
        while attempt <= MAX_REQUEST_ATTEMPT_COUNT:
            attempt += 1
            conn = aiohttp.TCPConnector(ssl=False)
            try:
                async with aiohttp.request(
                    method, f"{self.api_url}/{path}", params=params, connector=conn
                ) as resp:
                    if resp.status >= 400:
                        # retry on server errors or request timeout w/ increasing delay
                        if resp.status >= 500 or resp.status == 408:
                            if attempt < MAX_REQUEST_ATTEMPT_COUNT:
                                _LOGGER.debug(
                                    "%s request to %s failed with code %d: %s."
                                    " Retrying...",
                                    method,
                                    path,
                                    resp.status,
                                    resp.reason,
                                )
                                await asyncio.sleep(
                                    attempt * REQUEST_RETRY_DELAY_INTERVAL
                                )
                                continue

                        if resp.status == 401:
                            raise InvalidToken()
                        else:
                            raise RequestError(resp)
                    try:
                        json = await resp.json()
                        if "error" in json and json["error"]:
                            raise RequestError(resp)
                        return json
                    except ContentTypeError as e:
                        text = await resp.text()
                        _LOGGER.warn("Unable to parse as JSON: %s", text)
                        raise e
            except (
                ClientConnectionError,
                asyncio.TimeoutError,
                ContentTypeError,
            ) as e:
                # catch connection exceptions to retry w/ increasing delay
                if attempt < MAX_REQUEST_ATTEMPT_COUNT:
                    _LOGGER.debug(
                        "%s request to %s failed with %s. Retrying...",
                        method,
                        path,
                        str(e),
                    )
                    await asyncio.sleep(attempt * REQUEST_RETRY_DELAY_INTERVAL)
                    continue
                else:
                    raise e
            finally:
                await conn.close()

    async def _start_server(self) -> None:
        """Start an event listener server."""
        # First, figure out what address to listen on. Open a connection to
        # the Hubitat hub and see what address it used. This assumes this
        # machine and the Hubitat hub are on the same network.
        with _open_socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((self.host, 80))
            address = s.getsockname()[0]

        self._server = server.create_server(
            self._process_event, address, self.port or 0, self.ssl_context
        )
        self._server.start()
        _LOGGER.debug(
            "Listening on %s:%d with SSL %s",
            address,
            self._server.port,
            "disabled" if self.ssl_context is None else "enabled",
        )

        await self.set_event_url(self.event_url)


@contextmanager
def _open_socket(*args: Any, **kwargs: Any) -> Iterator[socket.socket]:
    """Open a socket as a context manager."""
    s = socket.socket(*args, **kwargs)
    try:
        yield s
    finally:
        s.close()


def _get_event_port(port: Optional[int], event_url: Optional[str]) -> Optional[int]:
    """Given an optional port and event URL, return the event port"""
    if port is not None:
        return port
    if event_url is not None:
        u = urlparse(event_url)
        return u.port
    return None


def _get_event_url(port: Optional[int], event_url: Optional[str]) -> Optional[str]:
    """Given an optional port and event URL, return a complete event URL"""
    if event_url is not None:
        u = urlparse(event_url)
        if u.port is None and port is not None:
            return ParseResult(
                scheme=u.scheme,
                netloc=f"{u.hostname}:{port}",
                path=u.path,
                params=u.params,
                query=u.query,
                fragment=u.fragment,
            ).geturl()
        return event_url
    return None
