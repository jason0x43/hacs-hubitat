"""Support for Hubitat fans."""

from logging import getLogger
from math import modf
from typing import Any, Dict, List, Optional, Sequence

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .device import HubitatEntity
from .entities import create_and_add_entities
from .hubitatmaker import (
    DEFAULT_FAN_SPEEDS,
    Device,
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
    DeviceState,
)
from .types import EntityAdder

_LOGGER = getLogger(__name__)

_device_attrs = (
    DeviceAttribute.SWITCH,
    DeviceAttribute.SPEED,
)

_speeds = {}


class HubitatFan(HubitatEntity, FanEntity):
    """Representation of a Hubitat fan."""

    @property
    def device_attrs(self) -> Optional[Sequence[str]]:
        """Return this entity's associated attributes"""
        return _device_attrs

    @property
    def is_on(self) -> bool:
        """Return true if the entity is on."""
        if DeviceCapability.SWITCH in self._device.capabilities:
            return self.get_str_attr(DeviceAttribute.SWITCH) == DeviceState.ON
        return self.get_str_attr(DeviceAttribute.SPEED) != DeviceState.OFF

    @property
    def percentage(self) -> Optional[int]:
        """Return the current speed as a percentage."""
        speed = self.get_str_attr(DeviceAttribute.SPEED)
        _LOGGER.debug("hubitat speed: %s", speed)
        if speed is None or speed == "off":
            _LOGGER.debug("  returning None")
            return None
        if speed == "auto":
            _LOGGER.debug("  returning 100")
            return 100
        idx = self.speeds.index(speed)
        _LOGGER.debug(
            "  index is %d, step is %f, pct is %f",
            idx,
            self.percentage_step,
            round(self.percentage_step * (idx + 1)),
        )
        return round(self.percentage_step * (idx + 1))

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode"""
        if self.get_str_attr(DeviceAttribute.SPEED) == "auto":
            return "auto"
        return None

    @property
    def preset_modes(self) -> Optional[List[str]]:
        """Return a list of available preset modes."""
        if "auto" in self.speeds_and_modes:
            return ["auto"]
        return None

    @property
    def speed_count(self) -> int:
        """Return the number of speeds supported by this fan."""
        # Hubitat speeds include 'on', 'off', and 'auto'
        return len(self.speeds)

    @property
    def speeds(self) -> List[str]:
        """Return the list of speeds for this fan."""
        return [s for s in self.speeds_and_modes if s not in ["auto", "on", "off"]]

    @property
    def speeds_and_modes(self) -> List[str]:
        """Return the list of speeds and modes for this fan."""
        return (
            self._device.attributes[DeviceAttribute.SPEED].values or DEFAULT_FAN_SPEEDS
        )

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this fan."""
        return f"{super().unique_id}::fan"

    @property
    def old_unique_ids(self) -> List[str]:
        """Return the legacy unique ID for this fan."""
        old_ids = [super().unique_id]
        old_parent_ids = super().old_unique_ids
        old_ids.extend(old_parent_ids)
        return old_ids

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return FanEntityFeature.SET_SPEED

    async def async_turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the switch."""
        _LOGGER.debug(
            "Turning on %s with percent [%s] or preset[ %s]",
            self.name,
            percentage,
            preset_mode,
        )
        if preset_mode in self.speeds_and_modes:
            await self.send_command(DeviceCommand.SET_SPEED, preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        elif DeviceCapability.SWITCH in self._device.capabilities:
            await self.send_command(DeviceCommand.ON)
        else:
            await self.send_command(DeviceCommand.SET_SPEED, DeviceState.ON)

    async def async_turn_off(self) -> None:
        """Turn off the switch."""
        _LOGGER.debug("Turning off %s", self.name)
        if DeviceCapability.SWITCH in self._device.capabilities:
            await self.send_command(DeviceCommand.OFF)
        else:
            await self.send_command(DeviceCommand.SET_SPEED, DeviceState.OFF)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan."""
        _LOGGER.debug("setting percentage to %d", percentage)
        if percentage == 0:
            await self.send_command(DeviceCommand.SET_SPEED, DeviceState.OFF)
        else:
            step = self.percentage_step
            [stepFrac, stepInt] = modf(percentage / step)
            idx = int(stepInt)
            if stepFrac >= 0.5:
                idx += 1
            if idx == 0:
                await self.send_command(DeviceCommand.SET_SPEED, DeviceState.OFF)
            else:
                await self.send_command(DeviceCommand.SET_SPEED, self.speeds[idx - 1])


def is_fan(device: Device, overrides: Optional[Dict[str, str]] = None) -> bool:
    """Return True if device looks like a fan."""
    if overrides and device.id in overrides and overrides[device.id] != "fan":
        return False
    return DeviceCapability.FAN_CONTROL in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: EntityAdder
) -> None:
    """Initialize fan devices."""
    create_and_add_entities(hass, entry, async_add_entities, "fan", HubitatFan, is_fan)
