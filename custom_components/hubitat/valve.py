"""Support for Hubitat valves."""

import re
from logging import getLogger
from typing import TYPE_CHECKING, Unpack, override

from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from homeassistant.components.valve import (
    ValveDeviceClass,
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device import HubitatEntity, HubitatEntityArgs
from .entities import create_and_add_entities
from .hubitatmaker import Device, DeviceCapability, DeviceCommand

_LOGGER = getLogger(__name__)

_NAME_TEST = re.compile(r"\bgas\b", re.IGNORECASE)


class HubitatValve(HubitatEntity, ValveEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Representation of a Hubitat switch."""

    def __init__(
        self,
        **kwargs: Unpack[HubitatEntityArgs],
    ):
        """Initialize a Hubitat switch."""
        device_class: ValveDeviceClass = (
            ValveDeviceClass.GAS
            if _NAME_TEST.search(kwargs["device"].label)
            else ValveDeviceClass.WATER
        )

        HubitatEntity.__init__(self, device_class=device_class, **kwargs)
        ValveEntity.__init__(self)

        self._attr_unique_id: str | None = f"{super().unique_id}::valve"
        self._attr_reports_position: bool = False
        self._attr_supported_features: ValveEntityFeature = (  # pyright: ignore[reportIncompatibleVariableOverride]
            ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
        )
        self.load_state()

    @override
    def load_state(self):
        self._attr_is_open: bool = self._get_is_open()
        self._attr_is_closed: bool | None = self._get_is_closed()

    def _get_is_open(self) -> bool:
        """Return True if the valve is open."""
        return self.get_str_attr(DeviceAttribute.VALVE) == "open"

    def _get_is_closed(self) -> bool:
        """Return True if the valve is open."""
        return self.get_str_attr(DeviceAttribute.VALVE) == "closed"

    @property
    @override
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return (DeviceAttribute.VALVE,)

    @override
    async def async_open_valve(self) -> None:
        """Open the valve."""
        _LOGGER.debug(f"Opening {self.name}")
        await self.send_command(DeviceCommand.OPEN)

    @override
    async def async_close_valve(self) -> None:
        """Close the valve."""
        _LOGGER.debug(f"Closing {self.name}")
        await self.send_command(DeviceCommand.CLOSE)


def is_valve(device: Device, _overrides: dict[str, str] | None = None) -> bool:
    """Return True if device looks like a valve."""
    return DeviceCapability.VALVE in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize valve devices."""

    _ = create_and_add_entities(
        hass,
        config_entry,
        async_add_entities,
        "valve",
        HubitatValve,
        is_valve,
    )


if TYPE_CHECKING:
    from .hub import DEVICE_TYPECHECK, HUB_TYPECHECK

    test_valve = HubitatValve(
        hub=HUB_TYPECHECK,
        device=DEVICE_TYPECHECK,
    )
