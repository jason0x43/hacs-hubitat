"""Base module for Hubitat devices."""

from abc import ABC, abstractmethod
from logging import getLogger
from typing import Any, Dict, List, Optional, Union

from hubitatmaker import Device, Event, Hub as HubitatHub

from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity import Entity

from .const import CONF_HUBITAT_EVENT, DOMAIN

_LOGGER = getLogger(__name__)


class HubitatDevice(ABC):
    """Base class for Hubitat devices and event emitters."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a device."""
        self._hub: HubitatHub = kwargs["hub"]
        self._device: Device = kwargs["device"]
        self._id = f"{self._hub.host}::{self._hub.app_id}::{self._device['id']}"
        self._hub.add_device_listener(self._device["id"], self.handle_event)

    @property
    def device_id(self):
        """Return the hub-local id for this device."""
        return self._device["id"]

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self._device["label"],
            "manufacturer": "Hubitat",
            "model": self.type,
            "via_device": (DOMAIN, self._hub.mac),
        }

    @property
    def unique_id(self):
        """Return a unique for this device."""
        return self._id

    @property
    def name(self):
        """Return the display name of this device."""
        return self._device["label"]

    @property
    def type(self):
        """Return the type name of this device."""
        return self._device["name"]

    async def async_will_remove_from_hass(self):
        """Run when entity will be removed from hass."""
        self._hub.remove_device_listeners(self.device_id)

    @callback
    def get_attr(self, attr: str) -> Union[float, int, str, None]:
        """Get the current value of an attribute."""
        dev_attr = self._hub.get_device_attribute(self.device_id, attr)
        if dev_attr:
            return dev_attr["currentValue"]
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
    def get_str_attr(self, attr: str) -> Optional[str]:
        """Get the current value of an attribute."""
        val = self.get_attr(attr)
        if val is None:
            return None
        return str(val)

    @callback
    def get_attr_values(self, attr: str) -> Optional[List[str]]:
        """Get the possible values of an enum attribute."""
        dev_attr = self._hub.get_device_attribute(self.device_id, attr)
        if dev_attr:
            return dev_attr["values"]
        return None

    @abstractmethod
    def handle_event(self, event: Event):
        ...


class HubitatStatefulDevice(HubitatDevice, Entity):
    """A generic device with state."""

    # Hubitat will push device updates
    should_poll = False

    async def async_update(self):
        """Fetch new data for this device."""
        await self._hub.refresh_device(self.device_id)

    async def send_command(self, command: str, *args: Union[int, str]):
        """Send a command to this device."""
        arg = ",".join([str(a) for a in args])
        await self._hub.send_command(self.device_id, command, arg)
        _LOGGER.debug(f"sent %s to %s", command, self.device_id)

    def handle_event(self, event: Event):
        """Handle a device event."""
        self.async_schedule_update_ha_state()


class HubitatEventDevice(HubitatDevice):
    """An event emitting device."""

    def __init__(self, hass: HomeAssistant, hub: HubitatHub, device: Dict[str, Any]):
        """Initialize a device."""
        super().__init__(hub=hub, device=device)
        self.hass = hass

    def handle_event(self, event: Event):
        """Create a listener for device events."""
        # Only emit HA events for stateless Hubitat events, like button pushes
        if event["attribute"] == "pushed":
            self.hass.bus.async_fire(CONF_HUBITAT_EVENT, event)
            _LOGGER.debug("emitted event %s", event)
