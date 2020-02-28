"""Support for Hubitat fans."""

from logging import getLogger
from typing import Any, List, Optional

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

from homeassistant.components.fan import FanEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .device import HubitatEntity, get_hub

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


def is_fan(device: Device) -> bool:
    """Return True if device looks like a fan."""
    return CAP_FAN_CONTROL in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities,
) -> None:
    """Initialize fan devices."""
    hub = get_hub(hass, entry.entry_id)
    devices = hub.devices
    fans = [
        HubitatFan(hub=hub, device=devices[i]) for i in devices if is_fan(devices[i])
    ]
    async_add_entities(fans)
    _LOGGER.debug(f"Added entities for fans: {fans}")
