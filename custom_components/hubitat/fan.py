"""Support for Hubitat switches."""

from logging import getLogger
import re
from typing import Any, List, Optional

from hubitatmaker import (
    CAP_FAN_CONTROL,
    CMD_SET_LEVEL,
    CMD_OFF, 
    CMD_ON, 
    CMD_CYCLE_SPEED, 
    CMD_SET_SPEED,
    ATTR_SPEED, 
    Hub as HubitatHub
)

from homeassistant.components.fan import (
    FanEntity
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import color as color_util

from .const import DOMAIN
from .device import HubitatDevice

_LOGGER = getLogger(__name__)

class HubitatFan(HubitatDevice, FanEntity):
    """Representation of a Hubitat fan."""

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self.get_str_attr("switch") == "on"

    # @property
    # def brightness(self) -> Optional[int]:
    #     """Return the level of this fan."""
    #     level = self.get_int_attr("level")
    #     if level is None:
    #         return None
    #     return int(255 * level / 100)

    @property
    def speed(self) -> str:
        """Return the speed of this fan."""
        return self.get_str_attr(ATTR_SPEED)

    @property
    def speed_list(self) -> str:
        """Return the list of speeds for this fan."""
        return ["off", "low", "medium-low", "medium", "high", "auto"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        _LOGGER.debug(f"Turning on {self.name} with {kwargs}")
        if ATTR_SPEED in kwargs:
            await self.send_command(CMD_SET_SPEED, kwargs[ATTR_SPEED])
        else:
            await self.send_command(CMD_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        _LOGGER.debug(f"Turning off {self.name}")
        await self.send_command(CMD_OFF)



def is_fan(device) -> bool:
    """Return True if device looks like a switch."""
    if CAP_FAN_CONTROL in device["capabilities"]:
        return True
    return False


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities,
) -> None:
    """Initialize fan devices."""
    hub: HubitatHub = hass.data[DOMAIN][entry.entry_id].hub
    fan_devs = [d for d in hub.devices if is_fan(d)]
    fans: List[HubitatFan] = []
    for f in fan_devs:
        fans.append(HubitatFan(hub=hub, device=f))
    async_add_entities(fans)
    _LOGGER.debug(f"Added entities for fans: {fans}")
