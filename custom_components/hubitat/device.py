"""Classes for managing Hubitat devices."""

from datetime import datetime
from logging import getLogger
from typing import Any, NotRequired, TypedDict, Unpack

from typing_extensions import override

from homeassistant.core import callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .hub import Hub
from .hubitatmaker import Device, DeviceAttribute, Event
from .types import Removable, UpdateableEntity
from .util import get_hub_device_id

_LOGGER = getLogger(__name__)


class HubitatBase(Removable):
    """Base class for Hubitat entities and event emitters."""

    def __init__(self, hub: Hub, device: Device, temp: bool | None = False) -> None:
        """Initialize a device."""
        self._hub = hub
        self._device = device
        self._temp = temp

    @property
    def device_id(self) -> str:
        """Return the hub-local id for this device."""
        return self._device.id

    @property
    def device_name(self) -> str:
        """Return the hub-local name for this device."""
        return self._device.name

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
    def type(self) -> str:
        """Return the type name of this device."""
        return self._device.type

    @property
    def room(self) -> str | None:
        """Return the room name of this device."""
        return self._device.room

    @override
    async def async_will_remove_from_hass(self):
        """Run when entity will be removed from hass."""
        self._hub.remove_device_listeners(self.device_id)

    @callback
    def get_attr(self, attr: DeviceAttribute) -> float | int | str | datetime | None:
        """Get the current value of an attribute."""
        if attr in self._device.attributes:
            return self._device.attributes[attr].value
        return None

    @callback
    def get_attr_unit(self, attr: DeviceAttribute) -> str | None:
        """Get the unit of an attribute."""
        if attr in self._device.attributes:
            return self._device.attributes[attr].unit
        return None

    @callback
    def get_float_attr(self, attr: DeviceAttribute) -> float | None:
        """Get the current value of an attribute."""
        if attr in self._device.attributes:
            return self._device.attributes[attr].float_value

    @callback
    def get_int_attr(self, attr: DeviceAttribute) -> int | None:
        """Get the current value of an attribute."""
        if attr in self._device.attributes:
            return self._device.attributes[attr].int_value

    @callback
    def get_json_attr(self, attr: DeviceAttribute) -> dict[str, Any] | None:
        """Get the current value of an attribute."""
        if attr in self._device.attributes:
            return self._device.attributes[attr].json_value

    @callback
    def get_str_attr(self, attr: DeviceAttribute) -> str | None:
        """Get the current value of an attribute."""
        if attr in self._device.attributes:
            return self._device.attributes[attr].str_value


class HubitatEntityArgs(TypedDict):
    hub: Hub
    device: Device
    temp: NotRequired[bool]
    """Whether this entity is temporary"""


class HubitatEntity(HubitatBase, UpdateableEntity):
    """An entity related to a Hubitat device."""

    def __init__(
        self, device_class: str | None = None, **kwargs: Unpack[HubitatEntityArgs]
    ):
        """Initialize an entity."""
        HubitatBase.__init__(self, **kwargs)
        UpdateableEntity.__init__(self)

        self._attr_name = self._device.label
        self._attr_unique_id = get_hub_device_id(self._hub, self._device)
        self._attr_device_class = device_class

        # Sometimes entities may be temporary, created only to compute entity
        # metadata. Don't register device listeners for temprorary entities.
        temp: bool = kwargs.get("temp", False)
        if not temp:
            self._hub.add_device_listener(self._device.id, self.handle_event)

    @property
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
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

    async def send_command(self, command: str, *args: int | str | None) -> None:
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
        return f"<HubitatEventEmitter {self.device_name}>"
