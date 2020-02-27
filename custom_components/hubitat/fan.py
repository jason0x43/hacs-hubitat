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
    DEFAULT_FAN_SPEEDS,
    Device
)

from homeassistant.components.fan import (
    SPEED_OFF,
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
    def speed(self) -> Optional[str]:
        """Return the speed of this fan."""
        return self.get_str_attr(ATTR_SPEED)

    @property
    def speed_list(self) -> List[Any]:
        """Return the list of speeds for this fan."""
        return self._device.attributes[ATTR_SPEED].values or DEFAULT_FAN_SPEEDS

    async def async_turn_on(self, speed: Optional[str] = None, **kwargs):
        """Turn on the switch."""
        _LOGGER.debug("Turning on %s with speed [%s]", self.name, speed)
        if speed is not None:
            await self.async_set_speed(speed)
        else:
            await self.send_command(CMD_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        _LOGGER.debug("Turning off %s", self.name)
        await self.send_command(CMD_OFF)

    async def async_set_speed(self, speed: str):
        """Set the speed of the fan."""
        if speed is SPEED_OFF:
            await self.async_turn_off()
        else:
            await self.send_command(CMD_SET_SPEED, speed)



def is_fan(device) -> bool:
    """Return True if device looks like a fan."""
    return CAP_FAN_CONTROL in device["capabilities"]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities,
) -> None:
    """Initialize fan devices."""
    hub = get_hub(hass, entry.entry_id)
    devices = hub.devices
    fans = [HubitatFan(hub=hub, device=devices[i]) for i in devices if is_fan(devices[i])]
    async_add_entities(fans)
    _LOGGER.debug(f"Added entities for fans: {fans}")
