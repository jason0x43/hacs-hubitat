"""Base module for Hubitat devices."""

from logging import getLogger
from typing import Any, Dict, List, Union

from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .hubitat import HubitatHub

_LOGGER = getLogger(__name__)


class HubitatDevice(Entity):
    """A generic Hubitat device."""

    # Hubitat will push device updates
    should_poll = False

    def __init__(self, hub: HubitatHub = None, device: Dict[str, Any] = None):
        """Initialize a device."""
        self._hub = hub
        self._device: Dict[str, Any] = device
        self._id = f"{self._hub.id}:{self._device['id']}"
        self._hub.add_device_listener(self._device["id"], self._create_listener())

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
            "via_device": (DOMAIN, self._hub.id),
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

    async def async_update(self):
        """Fetch new data for this device."""
        await self._hub.refresh_device(self.device_id)

    async def async_will_remove_from_hass(self):
        """Run when entity will be removed from hass."""
        self._hub.remove_device_listeners(self.device_id)

    async def _send_command(self, command: str, *args: List[Union[int, str]]):
        """Send a command to this device."""
        arg = ",".join([str(a) for a in args])
        await self._hub.send_command(self.device_id, command, arg)

    def _get_attr(self, attr: str):
        """Get the current value of an attribute."""
        dev_attr = self._hub.get_device_attribute(self.device_id, attr)
        return dev_attr["currentValue"]

    def _create_listener(self):
        def handle_event():
            self.async_schedule_update_ha_state()

        return handle_event
