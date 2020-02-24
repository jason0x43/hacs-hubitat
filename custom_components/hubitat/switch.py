"""Support for Hubitat switches."""

from logging import getLogger
import re
from typing import Any, List, Optional

from hubitatmaker import CAP_POWER_METER, CAP_SWITCH, CMD_OFF, CMD_ON, Hub as HubitatHub

from homeassistant.components.switch import (
    DEVICE_CLASS_OUTLET,
    DEVICE_CLASS_SWITCH,
    SwitchDevice,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import color as color_util

from .const import DOMAIN
from .device import HubitatDevice
from .light import is_light
from .fan import is_fan

_LOGGER = getLogger(__name__)

_NAME_TEST = re.compile(r"\bswitch\b", re.IGNORECASE)


class HubitatSwitch(HubitatDevice, SwitchDevice):
    """Representation of a Hubitat switch."""

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self.get_str_attr("switch") == "on"

    @property
    def device_class(self) -> str:
        """Return the class of this device, from component DEVICE_CLASSES."""
        if _NAME_TEST.match(self._device["label"]):
            return DEVICE_CLASS_SWITCH
        return DEVICE_CLASS_OUTLET

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        _LOGGER.debug(f"Turning on {self.name} with {kwargs}")
        await self.send_command(CMD_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        _LOGGER.debug(f"Turning off {self.name}")
        await self.send_command("off")


class HubitatPowerMeterSwitch(HubitatSwitch):
    @property
    def current_power_w(self) -> Optional[float]:
        """Return the current power usage in W."""
        return self.get_float_attr("power")


def is_switch(device) -> bool:
    """Return True if device looks like a switch."""
    if CAP_SWITCH in device["capabilities"] and not is_light(device) and not is_fan(device):
        return True
    return False


def is_energy_meter(device) -> bool:
    """Return True if device can measure power."""
    if CAP_POWER_METER in device["capabilities"]:
        return True
    return False


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities,
) -> None:
    """Initialize switch devices."""
    hub: HubitatHub = hass.data[DOMAIN][entry.entry_id].hub
    switch_devs = [d for d in hub.devices if is_switch(d)]
    switches: List[HubitatSwitch] = []
    for s in switch_devs:
        if is_energy_meter(s):
            switches.append(HubitatPowerMeterSwitch(hub=hub, device=s))
        else:
            switches.append(HubitatSwitch(hub=hub, device=s))
    async_add_entities(switches)
    _LOGGER.debug(f"Added entities for switches: {switches}")
