"""Classes for managing Hubitat devices."""

from abc import ABC
from datetime import datetime
from logging import getLogger
from typing import Any, TypedDict, Unpack

from typing_extensions import override

from homeassistant.core import callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .hub import Hub
from .hubitatmaker import Device, DeviceAttribute, Event
from .types import Removable, UpdateableEntity
from .util import get_device_identifiers, get_hub_device_id

_LOGGER = getLogger(__name__)


class HubitatBase(Removable):
    """Base class for Hubitat entities and event emitters."""

    def __init__(self, hub: Hub, device: Device) -> None:
        """Initialize a device."""
        self._hub: Hub = hub
        self._device: Device = device

    @property
    def device_id(self) -> str:
        """Return the hub-local id for this device."""
        return self._device.id

    @property
    def device_name(self) -> str:
        """Return the hub-local name for this device."""
        return self._device.name

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
        """Get the current value of an attribute as a float."""
        if attr in self._device.attributes:
            return self._device.attributes[attr].float_value

    @callback
    def get_int_attr(self, attr: DeviceAttribute) -> int | None:
        """Get the current value of an attribute as an int."""
        if attr in self._device.attributes:
            return self._device.attributes[attr].int_value

    @callback
    def get_list_attr(self, attr: DeviceAttribute) -> list[Any] | None:
        """Get the current value of an attribute as a list."""
        if attr in self._device.attributes:
            return self._device.attributes[attr].list_value

    @callback
    def get_dict_attr(self, attr: DeviceAttribute) -> dict[str, Any] | None:
        """Get the current value of an attribute as a dict."""
        if attr in self._device.attributes:
            return self._device.attributes[attr].dict_value

    @callback
    def get_str_attr(self, attr: DeviceAttribute) -> str | None:
        """Get the current value of an attribute as a string."""
        if attr in self._device.attributes:
            return self._device.attributes[attr].str_value


class HubitatEntityArgs(TypedDict):
    hub: Hub
    device: Device


class HubitatEntity(HubitatBase, Entity, UpdateableEntity, ABC):
    """An entity related to a Hubitat device."""

    def __init__(
        self,
        device_class: str | None = None,
        temp: bool = False,
        **kwargs: Unpack[HubitatEntityArgs],
    ):
        """
        Initialize an entity.

        Parameters
        ----------
        device_class : str | None
            The device class for this entity; default is None.
        temp : bool
            If true, this is a temporary entity; default is False
        """
        HubitatBase.__init__(self, **kwargs)
        UpdateableEntity.__init__(self)

        self._attr_name: str | None = self._device.label
        self._attr_unique_id: str | None = get_hub_device_id(self._hub, self._device)
        self._attr_device_class: str | None = device_class
        self._attr_should_poll: bool = False
        self._attr_device_info: device_registry.DeviceInfo | None = get_device_info(
            self._hub, self._device
        )
        if not temp:
            self._hub.add_device_listener(self._device.id, self.handle_event)
            _LOGGER.debug(
                "Added device listener for %s (%s)", self._device.id, self.__class__
            )

    def __del__(self):
        self._hub.remove_device_listener(self._device.id, self.handle_event)
        _LOGGER.debug(
            "Removed device listener for %s (%s)", self._device.id, self.__class__
        )

    @property
    @override
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        return None

    @override
    async def async_added_to_hass(self) -> None:
        _LOGGER.debug("Added %s with hass=%s", self, self.hass)

    async def async_update(self) -> None:
        """Fetch new data for this device."""
        await self._hub.refresh_device(self.device_id)

    async def send_command(self, command: str, *args: float | str | None) -> None:
        """Send a command to this device."""
        arg = ",".join([str(a) for a in args]) if args else None
        await self._hub.send_command(self.device_id, command, arg)
        _LOGGER.debug("sent %s to %s", command, self.device_id)

    def handle_event(self, _event: Event) -> None:
        """
        Handle a device event.

        If this entity is enabled, reload the entity state from the underlying
        device and tell HA that the state has updated.
        """
        _LOGGER.debug(f"handling event for {self} ({self.name}, {self.__class__})")
        if self.enabled:
            self.load_state()
            self.async_schedule_update_ha_state()


class HubitatEventEmitter(HubitatBase):
    """An event emitter related to a Hubitat device."""

    def update_device_registry(self) -> None:
        """Register a device for the event emitter."""
        # Create a device for the emitter since Home Assistant doesn't
        # automatically do that as it does for entities.
        entry = self._hub.config_entry
        dreg = device_registry.async_get(self._hub.hass)
        _ = dreg.async_get_or_create(
            config_entry_id=entry.entry_id, **get_device_info(self._hub, self._device)
        )
        _LOGGER.debug("Created device for %s", self)

    @override
    def __repr__(self) -> str:
        """Return the representation."""
        return f"<HubitatEventEmitter {self.device_name}>"


def get_device_info(hub: Hub, device: Device) -> device_registry.DeviceInfo:
    """Return the device info."""
    info: device_registry.DeviceInfo = {
        "identifiers": get_device_identifiers(hub.id, device.id)
    }

    # if this entity's device isn't the hub, link it to the hub
    if device.id != hub.id:
        info["name"] = device.label
        info["suggested_area"] = device.room
        info["via_device"] = (DOMAIN, hub.id)
        info["model"] = device.type
        info["manufacturer"] = "Hubitat"

    return info
