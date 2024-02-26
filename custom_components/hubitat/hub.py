import os
import ssl
from collections.abc import Mapping
from logging import getLogger
from ssl import SSLContext
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, TypeVar, cast

from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_HIDDEN,
    CONF_ACCESS_TOKEN,
    CONF_HOST,
    CONF_ID,
    CONF_TEMPERATURE_UNIT,
    UnitOfTemperature,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import area_registry, device_registry
from homeassistant.helpers.device_registry import DeviceEntry

try:
    from homeassistant.helpers.discovery_flow import (
        DiscoveryKey,  # pyright: ignore[reportAssignmentType]
    )
except Exception:

    class DiscoveryKey:
        pass


from .const import (
    ATTR_ATTRIBUTE,
    ATTR_HA_DEVICE_ID,
    ATTR_HUB,
    DOMAIN,
    H_CONF_APP_ID,
    H_CONF_HUBITAT_EVENT,
    H_CONF_SERVER_PORT,
    H_CONF_SERVER_SSL_CERT,
    H_CONF_SERVER_SSL_KEY,
    H_CONF_SERVER_URL,
    H_CONF_SYNC_AREAS,
    PLATFORMS,
    TEMP_F,
    TRIGGER_CAPABILITIES,
)
from .hubitatmaker import (
    Device,
    Event,
    Hub as HubitatHub,
)
from .types import Removable, UpdateableEntity
from .util import get_device_identifiers, get_hub_device_id, get_hub_short_id

_LOGGER = getLogger(__name__)

Listener = Callable[[Event], None]

HUB_DEVICE_NAME = "Hub"
HUB_NAME = "Hubitat Elevation"

# Hubitat attributes that should be emitted as HA events
_TRIGGER_ATTRS = tuple([v.attr for v in TRIGGER_CAPABILITIES.values()])
# A mapping from Hubitat attribute names to the attribute names that should be
# used for HA events
_TRIGGER_ATTR_MAP = {v.attr: v.event for v in TRIGGER_CAPABILITIES.values()}

E = TypeVar("E", bound=UpdateableEntity)
M = TypeVar("M", bound=Removable)


class Hub:
    """Representation of a Hubitat hub."""

    hass: HomeAssistant
    config_entry: ConfigEntry
    token: str
    unsub_config_listener: CALLBACK_TYPE
    device: Device

    _temperature_unit: str
    _hub_entity_id: str
    _hub_device_listeners: list[Listener]
    _device_listeners: dict[str, list[Listener]]
    _hub: HubitatHub

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        index: int,
        hub: HubitatHub,
        device: Device,
    ):
        """Initialize a Hubitat manager."""
        if CONF_HOST not in entry.data:
            raise ValueError("Missing host in config entry")
        if H_CONF_APP_ID not in entry.data:
            raise ValueError("Missing app ID in config entry")
        if CONF_ACCESS_TOKEN not in entry.data:
            raise ValueError("Missing access token in config entry")

        self.hass = hass
        self.config_entry = entry
        self.token = cast(str, self.config_entry.data.get(CONF_ACCESS_TOKEN))
        self.entities: list[UpdateableEntity] = []
        self.event_emitters: list[Removable] = []

        self._temperature_unit = (
            entry.options.get(
                CONF_TEMPERATURE_UNIT, entry.data.get(CONF_TEMPERATURE_UNIT)
            )
            or TEMP_F
        )

        if index == 1:
            self._hub_entity_id = "hubitat.hub"
        else:
            self._hub_entity_id = f"hubitat.hub_{index}"

        self.unsub_config_listener = entry.add_update_listener(_update_entry)
        self._hub_device_listeners = []
        self._device_listeners = {}
        self._hub = hub
        self.device = device

    @property
    def app_id(self) -> str:
        """The Maker API app ID for this hub."""
        return cast(str, self.config_entry.data.get(H_CONF_APP_ID))

    @property
    def devices(self) -> Mapping[str, Device]:
        """The Hubitat devices known to this hub."""
        return self._hub.devices

    @property
    def entity_id(self) -> str:
        """The entity ID of this hub."""
        return self._hub_entity_id

    @property
    def host(self) -> str:
        """The IP address of the  associated Hubitat hub."""
        return cast(
            str,
            self.config_entry.options.get(
                CONF_HOST, self.config_entry.data.get(CONF_HOST)
            ),
        )

    @property
    def id(self) -> str:
        """A unique ID for this hub instance."""
        return get_hub_short_id(self._hub)

    @property
    def port(self) -> int | None:
        """The port used for the Hubitat event receiver."""
        return self._hub.port

    @property
    def event_url(self) -> str | None:
        """The event URL that Hubitat should POST events to."""
        return self._hub.event_url

    @property
    def ssl_context(self) -> SSLContext | None:
        """The SSLContext that the event listener server is using."""
        return self._hub.ssl_context

    @property
    def mode(self) -> str | None:
        """Return the current mode of this hub."""
        return self._hub.mode

    @property
    def modes(self) -> list[str] | None:
        """Return the available modes of this hub."""
        return self._hub.modes

    @property
    def mode_supported(self) -> bool | None:
        """Return true if this hub supports mode setting and status."""
        return self._hub.mode_supported

    @property
    def hsm_status(self) -> str | None:
        """Return the current HSM status of this hub."""
        return self._hub.hsm_status

    @property
    def hsm_supported(self) -> bool | None:
        """Return true if this hub supports HSM setting and status."""
        return self._hub.hsm_supported

    @property
    def temperature_unit(self) -> UnitOfTemperature:
        """The units used for temperature values."""
        return (
            UnitOfTemperature.FAHRENHEIT
            if self._temperature_unit == TEMP_F
            else UnitOfTemperature.CELSIUS
        )

    def add_device_listener(self, device_id: str, listener: Listener) -> None:
        """Add a listener for events for a specific device."""
        if device_id == self.id:
            self._hub_device_listeners.append(listener)
        else:
            if device_id not in self._device_listeners:
                self._device_listeners[device_id] = []
            self._device_listeners[device_id].append(listener)

    def remove_device_listener(self, device_id: str, listener: Listener) -> None:
        """Remove a listener for events for a specific device."""
        if device_id == self.id:
            if listener in self._hub_device_listeners:
                self._hub_device_listeners.remove(listener)
        else:
            if (
                device_id in self._device_listeners
                and listener in self._device_listeners[device_id]
            ):
                self._device_listeners[device_id].remove(listener)

    def add_entities(self, entities: list[E]) -> None:
        """Add entities to this hub."""
        self.entities.extend(entities)

    def add_event_emitters(self, emitters: list[M]) -> None:
        """Add event emitters to this hub."""
        self.event_emitters.extend(emitters)

    def remove_device_listeners(self, device_id: str) -> None:
        """Remove all listeners for a specific device."""
        self._device_listeners[device_id] = []
        self._hub_device_listeners = []

    async def set_mode(self, mode: str) -> None:
        """Set the hub mode"""
        _LOGGER.debug("Setting hub mode to %s", mode)
        if self._hub:
            await self._hub.set_mode(mode)

    async def set_hsm(self, mode: str) -> None:
        """Set the hub HSM"""
        _LOGGER.debug("Setting hub HSM to %s", mode)
        if self._hub:
            await self._hub.set_hsm(mode)

    def set_temperature_unit(self, temp_unit: str) -> None:
        """Set the hub's temperature units."""
        _LOGGER.debug("Setting hub temperature unit to %s", temp_unit)
        self._temperature_unit = temp_unit

    def stop(self) -> None:
        """Stop the hub."""
        if self._hub:
            self._hub.stop()
        self._device_listeners = {}
        self._hub_device_listeners = []

    async def unload(self) -> None:
        """Unload the hub."""
        for emitter in self.event_emitters:
            await emitter.async_will_remove_from_hass()
        self.unsub_config_listener()

    @staticmethod
    async def create(hass: HomeAssistant, entry: ConfigEntry, index: int) -> "Hub":
        """Initialize this hub instance."""

        if CONF_HOST not in entry.data:
            raise ValueError("Missing host in config entry")
        if H_CONF_APP_ID not in entry.data:
            raise ValueError("Missing app ID in config entry")
        if CONF_ACCESS_TOKEN not in entry.data:
            raise ValueError("Missing access token in config entry")

        url = entry.options.get(H_CONF_SERVER_URL, entry.data.get(H_CONF_SERVER_URL))
        port = entry.options.get(H_CONF_SERVER_PORT, entry.data.get(H_CONF_SERVER_PORT))

        # Previous versions of the integration may have saved a value of "" for
        # server_url with the assumption that a use_server_url flag would control
        # it's use. The current version uses a value of null for "no user URL"
        # rather than a flag.
        if url == "":
            url = None

        ssl_cert = entry.options.get(
            H_CONF_SERVER_SSL_CERT,
            entry.data.get(H_CONF_SERVER_SSL_CERT),
        )
        ssl_key = entry.options.get(
            H_CONF_SERVER_SSL_KEY, entry.data.get(H_CONF_SERVER_SSL_KEY)
        )
        ssl_context = await hass.async_add_executor_job(
            _create_ssl_context, ssl_cert, ssl_key
        )

        host = cast(
            str,
            entry.options.get(CONF_HOST, entry.data.get(CONF_HOST)),
        )
        app_id = cast(str, entry.data.get(H_CONF_APP_ID))
        token = cast(str, entry.data.get(CONF_ACCESS_TOKEN))

        _LOGGER.debug(
            "Initializing Hubitat hub with event server on port %s with SSL %s",
            port,
            "disabled" if ssl_context is None else "enabled",
        )
        hubitat_hub = HubitatHub(
            host,
            app_id,
            token,
            port=port,
            event_url=url,
            ssl_context=ssl_context,
        )
        await hubitat_hub.start()

        # setup proxy Device representing the hub that can be used for linked
        # entities
        device = Device(
            {
                "id": get_hub_short_id(hubitat_hub),
                "name": HUB_DEVICE_NAME,
                "label": HUB_DEVICE_NAME,
                "model": "Cx",
                "manufacturer": HUB_NAME,
                "attributes": [
                    {
                        "name": "mode",
                        "currentValue": hubitat_hub.mode,
                        "dataType": "ENUM",
                    },
                    {
                        "name": "hsm_status",
                        "currentValue": hubitat_hub.hsm_status,
                        "dataType": "ENUM",
                    },
                ],
                "capabilities": [],
                "commands": [],
            }
        )

        hub = Hub(hass, entry, index, hubitat_hub, device)
        hass.data[DOMAIN][entry.entry_id] = hub

        # Add a listener for every device exported by the hub. The listener
        # will re-export the Hubitat event as a hubitat_event in HA if it
        # matches a trigger condition.
        for device_id in hubitat_hub.devices:
            hubitat_hub.add_device_listener(device_id, hub.handle_event)

        # Update device identifiers to include the Maker API instance ID to
        # ensure that devices coming from separate hubs (or Maker API installs)
        # are handled properly.
        if hub.id:
            _update_device_ids(hub.id, hass)

        # Initialize entities
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        _LOGGER.debug("Registered platforms")

        should_update_rooms = entry.options.get(
            H_CONF_SYNC_AREAS, entry.data.get(H_CONF_SYNC_AREAS)
        )
        if should_update_rooms:
            _update_device_rooms(hub, hass)

        # Create an entity for the Hubitat hub with basic hub information
        hass.states.async_set(
            hub.entity_id,
            "connected",
            {
                CONF_ID: f"{hubitat_hub.host}::{hubitat_hub.app_id}",
                CONF_HOST: hubitat_hub.host,
                ATTR_HIDDEN: True,
                CONF_TEMPERATURE_UNIT: hub.temperature_unit,
            },
        )

        if hub.mode_supported:

            def handle_mode_event(event: Event):
                device.update_attr(DeviceAttribute.MODE, cast(str, event.value), None)
                for listener in hub._hub_device_listeners:
                    listener(event)

            hub._hub.add_mode_listener(handle_mode_event)
            if hub.mode:
                hub.device.update_attr(DeviceAttribute.MODE, hub.mode, None)

        if hub.hsm_supported:

            def handle_hsm_status_event(event: Event):
                device.update_attr(
                    DeviceAttribute.HSM_STATUS, cast(str, event.value), None
                )
                for listener in hub._hub_device_listeners:
                    listener(event)

            hub._hub.add_hsm_listener(handle_hsm_status_event)
            if hub.hsm_status:
                hub.device.update_attr(DeviceAttribute.HSM_STATUS, hub.hsm_status, None)

        return hub

    def async_update_device_registry(self) -> None:
        """Add a device for this hub to the device registry."""
        dreg = device_registry.async_get(self.hass)
        _ = dreg.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            connections={(device_registry.CONNECTION_NETWORK_MAC, self._hub.mac)},
            identifiers={(DOMAIN, self.id)},
            manufacturer="Hubitat",
            name=HUB_NAME,
        )

    @staticmethod
    async def async_update_options(
        hass: HomeAssistant, config_entry: ConfigEntry
    ) -> None:
        """Handle options update."""
        _LOGGER.debug("Handling options update...")
        hub = get_hub(hass, config_entry.entry_id)

        host: str | None = config_entry.options.get(
            CONF_HOST, config_entry.data.get(CONF_HOST)
        )
        if host is not None and host != hub.host:
            await hub.set_host(host)
            _LOGGER.debug("Set hub host to %s", host)

        port = (
            config_entry.options.get(
                H_CONF_SERVER_PORT,
                config_entry.data.get(H_CONF_SERVER_PORT),
            )
            or 0
        )
        if port != hub.port:
            await hub.set_port(port)
            _LOGGER.debug("Set event server port to %s", port)

        url = config_entry.options.get(
            H_CONF_SERVER_URL, config_entry.data.get(H_CONF_SERVER_URL)
        )
        if url == "":
            url = None
        if url != hub.event_url:
            await hub.set_event_url(url)
            _LOGGER.debug("Set event server URL to %s", url)

        ssl_cert = config_entry.options.get(
            H_CONF_SERVER_SSL_CERT,
            config_entry.data.get(H_CONF_SERVER_SSL_CERT),
        )
        ssl_key = config_entry.options.get(
            H_CONF_SERVER_SSL_KEY,
            config_entry.data.get(H_CONF_SERVER_SSL_KEY),
        )
        ssl_context = await hass.async_add_executor_job(
            _create_ssl_context, ssl_cert, ssl_key
        )
        await hub.set_ssl_context(ssl_context)
        _LOGGER.debug(
            "Set event server SSL cert to %s and SSL key to %s", ssl_cert, ssl_key
        )

        temp_unit = (
            config_entry.options.get(
                CONF_TEMPERATURE_UNIT, config_entry.data.get(CONF_TEMPERATURE_UNIT)
            )
            or TEMP_F
        )
        if temp_unit != hub.temperature_unit:
            hub.set_temperature_unit(temp_unit)
            for entity in hub.entities:
                entity.load_state()
            _LOGGER.debug("Set temperature units to %s", temp_unit)

        hass.states.async_set(
            hub.entity_id,
            "connected",
            {CONF_HOST: hub.host, CONF_TEMPERATURE_UNIT: hub.temperature_unit},
        )

    async def check_config(self) -> None:
        """Verify that the hub is accessible."""
        await self._hub.check_config()

    async def refresh_device(self, device_id: str) -> None:
        """Load current data for a specific device."""
        await self._hub.refresh_device(device_id)

    async def send_command(
        self, device_id: str, command: str, arg: str | int | None
    ) -> None:
        """Send a device command to Hubitat."""
        _ = await self._hub.send_command(device_id, command, arg)

    async def set_host(self, host: str) -> None:
        """Set the host address that the Hubitat hub is accessible at."""
        _LOGGER.debug("Setting Hubitat host to %s", host)
        self._hub.set_host(host)

    async def set_port(self, port: int) -> None:
        """Set the port that the event listener server will listen on."""
        _LOGGER.debug("Setting event listener port to %s", port)
        await self._hub.set_port(port)

    async def set_ssl_context(self, ssl_context: SSLContext | None) -> None:
        """Set the SSLContext that the event listener server will use."""
        if ssl_context is None:
            _LOGGER.warning("Disabling SSL for event listener server")
        else:
            _LOGGER.warning("Enabling SSL for event listener server")
        await self._hub.set_ssl_context(ssl_context)

    async def set_event_url(self, url: str | None) -> None:
        """Set the port that the event listener server will listen on."""
        _LOGGER.debug("Setting event server URL to %s", url)
        await self._hub.set_event_url(url)

    def handle_event(self, event: Event) -> None:
        """Handle events received from the Hubitat hub."""
        if self._device_listeners[event.device_id]:
            for listener in self._device_listeners[event.device_id]:
                try:
                    listener(event)
                except Exception as e:
                    _LOGGER.warning(f"Error handling event {event}: {e}")
        if event.attribute in _TRIGGER_ATTRS:
            evt: dict[str, Any] = dict(event)
            evt[ATTR_ATTRIBUTE] = _TRIGGER_ATTR_MAP[event.attribute]
            evt[ATTR_HUB] = self.id
            evt[ATTR_HA_DEVICE_ID] = get_hub_device_id(self, event.device_id)
            self.hass.bus.async_fire(H_CONF_HUBITAT_EVENT, evt)
            _LOGGER.debug("Emitted event %s", evt)


async def _update_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    _ = await hass.config_entries.async_reload(config_entry.entry_id)


def get_hub(hass: HomeAssistant, config_entry_id: str) -> Hub:
    """Get the Hub device associated with a given config entry."""
    return cast(Hub, hass.data[DOMAIN][config_entry_id])


def _create_ssl_context(ssl_cert: str | None, ssl_key: str | None) -> SSLContext | None:
    if (
        ssl_cert is not None
        and os.path.isfile(ssl_cert)
        and ssl_key is not None
        and os.path.isfile(ssl_key)
    ):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(ssl_cert, ssl_key)
        return ssl_context
    else:
        return None


def _update_device_ids(hub_id: str, hass: HomeAssistant) -> None:
    dreg = device_registry.async_get(hass)
    all_devices = [dreg.devices[id] for id in dreg.devices]

    hubitat_devices: list[DeviceEntry] = []
    for dev in all_devices:
        ids = list(dev.identifiers)
        if len(ids) != 1:
            continue
        id_set = ids[0]
        if id_set[0] == DOMAIN and dev.name != HUB_NAME:
            hubitat_devices.append(dev)

    old_devs: dict[str, DeviceEntry] = {}
    new_devs: dict[str, DeviceEntry] = {}

    for dev in hubitat_devices:
        # Hubitat devices have 1 identifier tuple
        id_set = list(dev.identifiers)[0]

        if len(id_set) == 3:
            # devices created by v0.7.2b1 may have 3 values in the ID tuple
            new_devs[id_set[-1]] = dev
        elif len(id_set) == 2:
            if ":" in id_set[1]:
                # new device identifiers will use a string with the format
                # "hub_id:dev_id", like "abc123:23", as the second value
                hub_id, dev_id = id_set[1].split(":")

                if hub_id == dev_id:
                    # this is a dummy device with the identifier
                    # "hub_id:hub_id"; remove it.
                    dreg.async_remove_device(dev.id)
                    _LOGGER.info(f"Removed dummy device {dev.identifiers}")
                else:
                    try:
                        _ = int(dev_id)
                        new_devs[dev_id] = dev
                    except ValueError:
                        _LOGGER.warning(f"Device ID in unknown format: {id_set[1]}")
            else:
                try:
                    # old device identifiers will use the bare Hubitat device
                    # ID as the second value in the tuple
                    _ = int(id_set[1])
                    old_devs[id_set[1]] = dev
                except ValueError:
                    _LOGGER.warning(f"Device ID in unknown format: {id_set[1]}")
        else:
            _LOGGER.warning(f"Device identifier in unknown format: {id_set}")

    # Update any devices with 3-part identifiers to use 2-part identifiers in
    # the new format
    for id in new_devs:
        new_dev = new_devs[id]
        dev_ids = list(new_dev.identifiers)
        id_set = dev_ids[0]
        if len(id_set) == 3:
            new_ids = {
                (cast(tuple[str, str, str], id_set)[0], f"{id_set[1]}:{id_set[2]}")
            }
            _ = dreg.async_update_device(new_dev.id, new_identifiers=new_ids)
            _LOGGER.info(
                f"Updated identifiers of device {new_dev.identifiers} to {new_ids}"
            )

    for id in old_devs:
        dev = old_devs[id]
        if id in new_devs:
            # A new device exists with the same Hubitat device ID as this old
            # device; remove the old device
            dreg.async_remove_device(dev.id)
            _LOGGER.info(
                f"Removed device {dev.identifiers} in favor of "
                + f"{new_devs[id].identifiers}"
            )
        else:
            # No new device exists with the same Hubitat device ID as this old
            # device; update the identifiers of the old device to use the new
            # format
            dev_ids = list(dev.identifiers)
            id_set = dev_ids[0]
            new_ids = {(id_set[0], f"{hub_id}:{id_set[1]}")}
            _ = dreg.async_update_device(dev.id, new_identifiers=new_ids)
            _LOGGER.info(
                f"Updated identifiers of device {dev.identifiers} to {new_ids}"
            )


def _update_device_rooms(hub: Hub, hass: HomeAssistant) -> None:
    """Update the area ID of devices in Home Assistant to match the room from
    Hubitat
    """

    _LOGGER.debug("Synchronizing device rooms...")

    dreg = device_registry.async_get(hass)
    all_devices = [dreg.devices[id] for id in dreg.devices]
    hubitat_devices: list[DeviceEntry] = []
    for dev in all_devices:
        ids = list(dev.identifiers)
        if len(ids) != 1:
            continue
        id_set = ids[0]
        if id_set[0] == DOMAIN and dev.name != HUB_NAME:
            hubitat_devices.append(dev)

    areg = area_registry.async_get(hass)

    for device_id in hub.devices:
        # if the device area from Hubitat is defined and differs from
        # Home Assistant, update the device area ID
        device = hub.devices[device_id]
        identifiers = get_device_identifiers(hub.id, device.id)
        hass_device = dreg.async_get_device(identifiers)

        if not hass_device:
            _LOGGER.debug(
                "Skipping room check for %s because no HA device", device.name
            )
            continue

        if device.room:
            area = areg.async_get_or_create(device.room)
            if hass_device.area_id != area.id:
                _ = dreg.async_update_device(hass_device.id, area_id=area.id)
                _LOGGER.debug("Updated location of %s to %s", device.name, area.id)
        elif hass_device.area_id:
            _ = dreg.async_clear_area_id(hass_device.id)
            _LOGGER.debug("Cleared location of %s", device.name)


if TYPE_CHECKING:
    test_hass = HomeAssistant("")
    test_discovery_keys: MappingProxyType[str, tuple[DiscoveryKey, ...]] = (
        MappingProxyType({})
    )
    test_entry = ConfigEntry(
        version=1,
        domain="Hubitat",
        title="Hubitat",
        data={},
        source="",
        minor_version=0,  # type: ignore
        discovery_keys=test_discovery_keys,  # pyright: ignore[reportArgumentType]
        options=None,
        unique_id=None,
    )
    hubitat_hub = HubitatHub("", "", "")
    device = Device({})
    HUB_TYPECHECK = Hub(
        hass=test_hass, entry=test_entry, index=0, hub=hubitat_hub, device=device
    )
    DEVICE_TYPECHECK = Device({})
