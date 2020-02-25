"""Classes for managing Hubitat devices."""

from abc import ABC, abstractmethod
from json import loads
from logging import getLogger
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union, cast

from hubitatmaker import (
    CAP_COLOR_CONTROL,
    CAP_COLOR_TEMP,
    CAP_CONTACT_SENSOR,
    CAP_ILLUMINANCE_MEASUREMENT,
    CAP_MOTION_SENSOR,
    CAP_MUSIC_PLAYER,
    CAP_POWER_METER,
    CAP_PUSHABLE_BUTTON,
    CAP_RELATIVE_HUMIDITY_MEASUREMENT,
    CAP_SWITCH,
    CAP_SWITCH_LEVEL,
    CAP_TEMPERATURE_MEASUREMENT,
    Device,
    Event,
    Hub as HubitatHub,
)

from homeassistant.components.sensor import DEVICE_CLASS_TEMPERATURE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_HIDDEN,
    CONF_ACCESS_TOKEN,
    CONF_HOST,
    CONF_ID,
    CONF_TEMPERATURE_UNIT,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import Entity

from .const import (
    CONF_APP_ID,
    CONF_HUBITAT_EVENT,
    CONF_SERVER_PORT,
    DOMAIN,
    PLATFORMS,
    TEMP_F,
    TRIGGER_CAPABILITIES,
)

_TRIGGER_ATTRS = tuple([v["attr"] for v in TRIGGER_CAPABILITIES.values()])

_LOGGER = getLogger(__name__)

Listener = Callable[[Event], None]


class Hub:
    """Representation of a Hubitat hub."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, index: int):
        """Initialize a Hubitat manager."""
        if not CONF_HOST in entry.data:
            raise ValueError(f"Missing host in config entry")
        if not CONF_APP_ID in entry.data:
            raise ValueError(f"Missing app ID in config entry")
        if not CONF_ACCESS_TOKEN in entry.data:
            raise ValueError(f"Missing access token in config entry")

        self.hass = hass
        self.config_entry = entry
        self.entities: List["HubitatEntity"] = []
        self.event_emitters: List["HubitatEventEmitter"] = []

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

        entry.add_update_listener(self.async_update_options)

    @property
    def app_id(self) -> str:
        return cast(str, self.config_entry.data.get(CONF_APP_ID))

    @property
    def devices(self) -> Mapping[str, Device]:
        return self._hub.devices

    @property
    def entity_id(self) -> str:
        return self._hub_entity_id

    @property
    def host(self) -> str:
        return cast(str, self.config_entry.data.get(CONF_HOST))

    @property
    def mac(self) -> str:
        return self._hub.mac

    @property
    def port(self) -> Optional[int]:
        return self._hub.port

    @property
    def token(self) -> str:
        return cast(str, self.config_entry.data.get(CONF_ACCESS_TOKEN))

    @property
    def temperature_unit(self) -> str:
        return self._temperature_unit

    def add_device_listener(self, device_id: str, listener: Listener):
        return self._hub.add_device_listener(device_id, listener)

    def add_entities(self, entities: Sequence["HubitatEntity"]) -> None:
        self.entities.extend(entities)

    def add_event_emitters(self, emitters: Sequence["HubitatEventEmitter"]) -> None:
        self.event_emitters.extend(emitters)

    def remove_device_listeners(self, device_id: str) -> None:
        self._hub.remove_device_listeners(device_id)

    def set_temperature_unit(self, temp_unit: str) -> None:
        """Set the hub's temperature units."""
        _LOGGER.debug("Setting hub temperature unit to %s", temp_unit)
        self._temperature_unit = temp_unit

    def stop(self) -> None:
        self._hub.stop()

    def unload(self) -> None:
        for emitter in self.event_emitters:
            emitter.async_will_remove_from_hass()

    async def async_setup(self) -> bool:
        entry = self.config_entry
        port = (
            entry.options.get(CONF_SERVER_PORT, entry.data.get(CONF_SERVER_PORT)) or 0
        )

        _LOGGER.debug("Initializing Hubitat hub with event server on port %s", port)
        self._hub = HubitatHub(self.host, self.app_id, self.token, port)

        await self._hub.start()

        hub = self._hub
        hass = self.hass
        config_entry = self.config_entry

        for component in PLATFORMS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(config_entry, component)
            )
        _LOGGER.debug(f"Registered platforms")

        # Create an entity for the Hubitat hub with basic hub information
        hass.states.async_set(
            self.entity_id,
            "connected",
            {
                CONF_ID: f"{hub.host}::{hub.app_id}",
                CONF_HOST: hub.host,
                ATTR_HIDDEN: True,
                CONF_TEMPERATURE_UNIT: self.temperature_unit,
            },
        )

        return True

    async def async_update_device_registry(self) -> None:
        """Add a device for this hub to the device registry."""
        dreg = await device_registry.async_get_registry(self.hass)
        dreg.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            connections={(device_registry.CONNECTION_NETWORK_MAC, self._hub.mac)},
            identifiers={(DOMAIN, self._hub.mac)},
            manufacturer="Hubitat",
            name="Hubitat Elevation",
        )

    @staticmethod
    async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle options update."""
        hub = get_hub(hass, entry.entry_id)

        port = (
            entry.options.get(CONF_SERVER_PORT, entry.data.get(CONF_SERVER_PORT)) or 0
        )
        if port != hub.port:
            await hub.set_port(port)

        temp_unit = (
            entry.options.get(
                CONF_TEMPERATURE_UNIT, entry.data.get(CONF_TEMPERATURE_UNIT)
            )
            or TEMP_F
        )
        if temp_unit != hub.temperature_unit:
            hub.set_temperature_unit(temp_unit)
            for entity in hub.entities:
                if entity.device_class == DEVICE_CLASS_TEMPERATURE:
                    entity.async_schedule_update_ha_state()

        hass.states.async_set(
            hub.entity_id, "connected", {CONF_TEMPERATURE_UNIT: hub.temperature_unit}
        )

    async def check_config(self) -> None:
        """Verify that the hub is accessible."""
        await self._hub.check_config()

    async def refresh_device(self, device_id: str) -> None:
        await self._hub.refresh_device(device_id)

    async def send_command(
        self, device_id: str, command: str, arg: Optional[Union[str, int]]
    ) -> None:
        """Send a device command to Hubitat."""
        await self._hub.send_command(device_id, command, arg)

    async def set_port(self, port: int) -> None:
        """Set the port that the event listener server will listen on."""
        _LOGGER.debug("Setting event listener port to %s", port)
        await self._hub.set_port(port)


class HubitatBase(ABC):
    """Base class for Hubitat entities and event emitters."""

    def __init__(self, hub: Hub, device: Device):
        """Initialize a device."""
        self._hub = hub
        self._device: Device = device
        self._id = f"{self._hub.host}::{self._hub.app_id}::{self._device.id}"
        self._hub.add_device_listener(self._device.id, self.handle_event)

    @property
    def device_id(self) -> str:
        """Return the hub-local id for this device."""
        return self._device.id

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return the device info."""
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self._device.name,
            "manufacturer": "Hubitat",
            "model": self.type,
            "via_device": (DOMAIN, self._hub.mac),
        }

    @property
    def unique_id(self) -> str:
        """Return a unique for this device."""
        return self._id

    @property
    def name(self) -> str:
        """Return the display name of this device."""
        return self._device.name

    @property
    def type(self) -> str:
        """Return the type name of this device."""
        return self._device.type

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        self._hub.remove_device_listeners(self.device_id)

    @callback
    def get_attr(self, attr: str) -> Union[float, int, str, None]:
        """Get the current value of an attribute."""
        if attr in self._device.attributes:
            return self._device.attributes[attr].value
        return None

    @callback
    def get_float_attr(self, attr: str) -> Optional[float]:
        """Get the current value of an attribute."""
        val = self.get_attr(attr)
        if val is None:
            return None
        return float(val)

    @callback
    def get_int_attr(self, attr: str) -> Optional[int]:
        """Get the current value of an attribute."""
        val = self.get_float_attr(attr)
        if val is None:
            return None
        return round(val)

    @callback
    def get_json_attr(self, attr: str) -> Optional[Dict[str, Any]]:
        """Get the current value of an attribute."""
        val = self.get_str_attr(attr)
        if val is None:
            return None
        return loads(val)

    @callback
    def get_str_attr(self, attr: str) -> Optional[str]:
        """Get the current value of an attribute."""
        val = self.get_attr(attr)
        if val is None:
            return None
        return str(val)

    @abstractmethod
    def handle_event(self, event: Event) -> None:
        ...


class HubitatEntity(HubitatBase, Entity):
    """An entity related to a Hubitat device."""

    # Hubitat will push device updates
    should_poll = False

    async def async_update(self) -> None:
        """Fetch new data for this device."""
        await self._hub.refresh_device(self.device_id)

    async def send_command(self, command: str, *args: Union[int, str]) -> None:
        """Send a command to this device."""
        arg = ",".join([str(a) for a in args])
        await self._hub.send_command(self.device_id, command, arg)
        _LOGGER.debug(f"sent %s to %s", command, self.device_id)

    def handle_event(self, event: Event) -> None:
        """Handle a device event."""
        self.async_schedule_update_ha_state()


class HubitatEventEmitter(HubitatBase):
    """An event emitter related to a Hubitat device."""

    async def update_device_registry(self) -> None:
        """Register a device for the event emitter."""
        # Create a device for the emitter since Home Assistant doesn't
        # automatically do that as it does for entities.
        entry = self._hub.config_entry
        dreg = await device_registry.async_get_registry(self._hub.hass)
        dreg.async_get_or_create(config_entry_id=entry.entry_id, **self.device_info)
        _LOGGER.debug("Created device for %s", self)

    def handle_event(self, event: Event) -> None:
        """Create a listener for device events."""
        # Only emit HA events for stateless Hubitat events, like button pushes
        if event.attribute in _TRIGGER_ATTRS:
            self._hub.hass.bus.async_fire(CONF_HUBITAT_EVENT, dict(event))
            _LOGGER.debug("emitted event %s", event)


def get_hub(hass: HomeAssistant, entry_id: str) -> Hub:
    """Get the Hub device associated with a given config entry."""
    return hass.data[DOMAIN][entry_id]
