"""Support for Hubitat fans."""

from hubitatmaker import (
    ATTR_SPEED,
    ATTR_SWITCH,
    CAP_FAN_CONTROL,
    CAP_SWITCH,
    CMD_OFF,
    CMD_ON,
    CMD_SET_SPEED,
    DEFAULT_FAN_SPEEDS,
    STATE_LOW,
    STATE_OFF,
    STATE_ON,
    Device,
)
from logging import getLogger
from typing import Any, Dict, List, Optional

from homeassistant.components.fan import SUPPORT_SET_SPEED, FanEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .device import HubitatEntity
from .entities import create_and_add_entities
from .types import EntityAdder

_LOGGER = getLogger(__name__)


class HubitatFan(HubitatEntity, FanEntity):
    """Representation of a Hubitat fan."""

    @property
    def is_on(self) -> bool:
        if CAP_SWITCH in self._device.capabilities:
            return self.get_str_attr(ATTR_SWITCH) == STATE_ON
        return self.get_str_attr(ATTR_SPEED) != STATE_OFF

    @property
    def speed(self) -> Optional[str]:
        """Return the speed of this fan."""
        return self.get_str_attr(ATTR_SPEED)

    @property
    def speed_list(self) -> List[str]:
        """Return the list of speeds for this fan."""
        return self._device.attributes[ATTR_SPEED].values or DEFAULT_FAN_SPEEDS

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
        return SUPPORT_SET_SPEED

    async def async_turn_on(self, speed: Optional[str] = None, **kwargs: Any) -> None:
        """Turn on the switch."""
        _LOGGER.debug("Turning on %s with speed [%s]", self.name, speed)
        if speed is not None:
            await self.async_set_speed(speed)
        elif CAP_SWITCH in self._device.capabilities:
            await self.send_command(CMD_ON)
        else:
            await self.async_set_speed(STATE_LOW)

    async def async_turn_off(self) -> None:
        """Turn off the switch."""
        _LOGGER.debug("Turning off %s", self.name)
        if CAP_SWITCH in self._device.capabilities:
            await self.send_command(CMD_OFF)
        else:
            await self.async_set_speed(STATE_OFF)

    async def async_set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        await self.send_command(CMD_SET_SPEED, speed)


def is_fan(device: Device, overrides: Optional[Dict[str, str]] = None) -> bool:
    """Return True if device looks like a fan."""
    if overrides and device.id in overrides and overrides[device.id] != "fan":
        return False
    return CAP_FAN_CONTROL in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: EntityAdder
) -> None:
    """Initialize fan devices."""
    create_and_add_entities(hass, entry, async_add_entities, "fan", HubitatFan, is_fan)
