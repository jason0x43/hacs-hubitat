"""Support for Hubitat fans."""

from logging import getLogger
import re
from typing import Any, List, Optional

from hubitatmaker import (
    ATTR_SWITCH,
    ATTR_SPEED,
    CAP_FAN_CONTROL,
    CMD_SET_LEVEL,
    CMD_OFF, 
    CMD_ON, 
    CMD_CYCLE_SPEED, 
    CMD_SET_SPEED,
    Device
)

from homeassistant.components.fan import (
    FanEntity
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import color as color_util

from .device import Hub, HubitatEntity, get_hub
_LOGGER = getLogger(__name__)

class HubitatFan(HubitatEntity, FanEntity):
    """Representation of a Hubitat fan."""

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self.get_str_attr(ATTR_SWITCH) == "on"

    @property
    def speed(self) -> str:
        """Return the speed of this fan."""
        return self.get_str_attr(ATTR_SPEED)

    @property
    def speed_list(self) -> str:
        """Return the list of speeds for this fan. (MakerAPI isn't sending the list of speeds)"""
        return ["off", "low", "medium-low", "medium", "high", "auto"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        _LOGGER.debug("Turning on %s with %s", self.name, kwargs)
        if ATTR_SPEED in kwargs:
            await self.send_command(CMD_SET_SPEED, kwargs[ATTR_SPEED])
        else:
            await self.send_command(CMD_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        _LOGGER.debug("Turning off %s", self.name)
        await self.send_command(CMD_OFF)



def is_fan(device) -> bool:
    """Return True if device looks like a fan."""
    return  CAP_FAN_CONTROL in device["capabilities"]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities,
) -> None:
    """Initialize fan devices."""
    hub = get_hub(hass, entry.entry_id)
    devices = hub.devices
    fan_devs = [d for d in devices if is_fan(d)]
    fans: List[HubitatFan] = []
    for f in fan_devs:
        fans.append(HubitatFan(hub=hub, device=f))
    async_add_entities(fans)
    _LOGGER.debug(f"Added entities for fans: {fans}")
