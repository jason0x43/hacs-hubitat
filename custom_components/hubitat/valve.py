"""Support for Hubitat valves."""

import re
from logging import getLogger
from typing import TYPE_CHECKING, Any, Unpack

from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from homeassistant.components.valve import ValveDeviceClass, ValveEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device import HubitatEntity, HubitatEntityArgs
from .entities import create_and_add_entities
from .hubitatmaker import Device, DeviceCapability, DeviceCommand

_LOGGER = getLogger(__name__)

_NAME_TEST = re.compile(r"\bgas\b", re.IGNORECASE)


class HubitatValve(HubitatEntity, ValveEntity):
    """Representation of a Hubitat switch."""

    def __init__(
        self,
        **kwargs: Unpack[HubitatEntityArgs],
    ):
        """Initialize a Hubitat switch."""
        HubitatEntity.__init__(self, **kwargs)
        ValveEntity.__init__(self)
        self._attr_device_class = (
            ValveDeviceClass.GAS
            if _NAME_TEST.search(self._device.label)
            else ValveDeviceClass.WATER
        )
        self._attr_unique_id = f"{super().unique_id}::valve"
        self.load_state()

    def load_state(self):
        self._attr_is_opening = self._get_is_open()

    def _get_is_open(self) -> bool:
        """Return True if the valve is open."""
        return self.get_str_attr(DeviceAttribute.VALVE) == "open"

    @property
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return (DeviceAttribute.VALVE,)

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        _LOGGER.debug(f"Opening {self.name} with {kwargs}")
        await self.send_command(DeviceCommand.OPEN)

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Close the valve."""
        _LOGGER.debug(f"Closing {self.name}")
        await self.send_command(DeviceCommand.CLOSE)


def is_valve(device: Device, overrides: dict[str, str] | None = None) -> bool:
    """Return True if device looks like a valve."""
    return DeviceCapability.VALVE in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize valve devices."""

    create_and_add_entities(
        hass,
        config_entry,
        async_add_entities,
        "switch",
        HubitatValve,
        is_valve,
    )


if TYPE_CHECKING:
    from .hub import DEVICE_TYPECHECK, HUB_TYPECHECK

    test_valve = HubitatValve(
        hub=HUB_TYPECHECK,
        device=DEVICE_TYPECHECK,
    )
