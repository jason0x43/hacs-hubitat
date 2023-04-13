"""Classes for managing Hubitat devices."""

from json import loads
from logging import getLogger
from typing import Any, Dict, List, Optional, Union, cast

from homeassistant.core import callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .hub import Hub
from .hubitatmaker import Device, Event
from .types import Removable, UpdateableEntity
from .util import get_hub_device_id

_LOGGER = getLogger(__name__)


class HubitatBase(Removable):
    """Base class for Hubitat entities and event emitters."""

    def __init__(self, hub: Hub, device: Device, temp: Optional[bool] = False) -> None:
        """Initialize a device."""
        self._hub = hub
        self._device = device
        self._id = get_hub_device_id(hub, device)
        self._old_ids = [
            f"{self._hub.host}::{self._hub.app_id}::{self._device.id}",
        ]
        self._temp = temp

    @property
    def device_id(self) -> str:
        """Return the hub-local id for this device."""
        return self._device.id

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        dev_identifier = self.device_id
        if self._hub.id != self.device_id:
            dev_identifier = f"{self._hub.id}:{self.device_id}"

        info: DeviceInfo = {
            "identifiers": {(DOMAIN, dev_identifier)},
        }

        # if this entity's device isn't the hub, link it to the hub
        if self.device_id != self._hub.id:
            info["name"] = self._device.label
            info["suggested_area"] = self.room
            info["via_device"] = (DOMAIN, self._hub.id)
            info["model"] = self.type
            info["manufacturer"] = "Hubitat"

        return info

    @property
    def old_unique_ids(self) -> List[str]:
        """Return the legacy unique for this device."""
        return self._old_ids

    @property
    def unique_id(self) -> str:
        """Return a unique for this device."""
        return self._id

    @property
    def name(self) -> str:
        """Return the display name of this device."""
        return self._device.label

    @property
    def type(self) -> str:
        """Return the type name of this device."""
        return self._device.type

    @property
    def room(self) -> str | None:
        """Return the room name of this device."""
        return self._device.room

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
        return cast(Dict[str, Any], loads(val))

    @callback
    def get_str_attr(self, attr: str) -> Optional[str]:
        """Get the current value of an attribute."""
        val = self.get_attr(attr)
        if val is None:
            return None
        return str(val)

    @property
    def last_update(self) -> float:
        """Return the last update time of this device."""
        return self._device.last_update


class HubitatEntity(HubitatBase, UpdateableEntity):
    """An entity related to a Hubitat device."""

    def __init__(self, hub: Hub, device: Device, temp: Optional[bool] = False) -> None:
        """Initialize an entity."""
        super().__init__(hub, device, temp)

        # Sometimes entities may be temporary, created only to compute entity
        # metadata. Don't register device listeners for temprorary entities.
        if not temp:
            self._hub.add_device_listener(self._device.id, self.handle_event)

    @property
    def device_attrs(self) -> Optional[str]:
        return None

    @property
    def should_poll(self) -> bool:
        # Hubitat will push device updates
        return False

    @property
    def is_disabled(self) -> bool:
        """Indicate whether this device is currently disabled."""
        if self.registry_entry:
            return self.registry_entry.disabled_by is not None
        return False

    async def async_update(self) -> None:
        """Fetch new data for this device."""
        await self._hub.refresh_device(self.device_id)

    async def send_command(
        self, command: str, *args: Optional[Union[int, str]]
    ) -> None:
        """Send a command to this device."""
        arg = ",".join([str(a) for a in args]) if args else None
        await self._hub.send_command(self.device_id, command, arg)
        _LOGGER.debug("sent %s to %s", command, self.device_id)

    def handle_event(self, event: Event) -> None:
        """Handle a device event."""
        self.update_state()

    def update_state(self) -> None:
        """Request that Home Assistant update this device's state."""
        if not self.is_disabled:
            self.async_schedule_update_ha_state()


class HubitatEventEmitter(HubitatBase):
    """An event emitter related to a Hubitat device."""

    def update_device_registry(self) -> None:
        """Register a device for the event emitter."""
        # Create a device for the emitter since Home Assistant doesn't
        # automatically do that as it does for entities.
        entry = self._hub.config_entry
        dreg = device_registry.async_get(self._hub.hass)
        dreg.async_get_or_create(config_entry_id=entry.entry_id, **self.device_info)
        _LOGGER.debug("Created device for %s", self)

    def __repr__(self) -> str:
        """Return the representation."""
        return f"<HubitatEventEmitter {self.name}>"
