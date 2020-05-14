"""Support for Hubitat lights."""

import json
from logging import getLogger
import re
from typing import Any, Dict, List, Optional, Union

from hubitatmaker import (
    CAP_COLOR_CONTROL,
    CAP_COLOR_TEMP,
    CAP_LIGHT,
    CAP_SWITCH,
    CAP_SWITCH_LEVEL,
    CMD_ON,
    CMD_SET_COLOR,
    CMD_SET_COLOR_TEMP,
    CMD_SET_LEVEL,
    Device,
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    Light,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import color as color_util

from .cover import is_cover
from .device import HubitatEntity
from .entities import create_and_add_entities
from .types import EntityAdder

_LOGGER = getLogger(__name__)


class HubitatLight(HubitatEntity, Light):
    """Representation of a Hubitat light."""

    @property
    def brightness(self) -> Optional[int]:
        """Return the level of this light."""
        level = self.get_int_attr("level")
        if level is None:
            return None
        return int(255 * level / 100)

    @property
    def hs_color(self) -> Optional[List[float]]:
        """Return the hue and saturation color value [float, float]."""
        hue = self.get_float_attr("hue")
        sat = self.get_float_attr("saturation")
        if hue is None or sat is None:
            return None
        hass_hue = 360 * hue / 100
        return [hass_hue, sat]

    @property
    def color_temp(self) -> Optional[float]:
        """Return the CT color value in mireds."""
        temp = self.get_int_attr("colorTemperature")
        if temp is None:
            return None
        return color_util.color_temperature_kelvin_to_mired(temp)

    @property
    def is_on(self) -> bool:
        """Return True if the light is on."""
        return self.get_str_attr("switch") == "on"

    @property
    def supported_features(self) -> int:
        """Return supported feature flags."""
        features = 0
        caps = self._device.capabilities

        if CAP_COLOR_CONTROL in caps:
            features |= SUPPORT_COLOR
        if CAP_COLOR_TEMP in caps:
            features |= SUPPORT_COLOR_TEMP
        if CAP_SWITCH_LEVEL in caps:
            features |= SUPPORT_BRIGHTNESS

        return features

    def supports_feature(self, feature) -> bool:
        """Return True if light supports a given feature."""
        return self.supported_features & feature != 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        _LOGGER.debug(f"Turning on {self.name} with {kwargs}")

        props: Dict[str, Union[int, str]] = {}

        if ATTR_BRIGHTNESS in kwargs and self.supports_feature(SUPPORT_BRIGHTNESS):
            props["level"] = int(100 * kwargs[ATTR_BRIGHTNESS] / 255)

        if ATTR_TRANSITION in kwargs:
            props["time"] = kwargs[ATTR_TRANSITION]

        if ATTR_HS_COLOR in kwargs and self.supports_feature(SUPPORT_COLOR):
            # Hubitat hue is from 0 - 100
            props["hue"] = int(100 * kwargs[ATTR_HS_COLOR][0] / 360)
            props["sat"] = kwargs[ATTR_HS_COLOR][1]

        if ATTR_COLOR_TEMP in kwargs and self.supports_feature(SUPPORT_COLOR_TEMP):
            mireds = kwargs[ATTR_COLOR_TEMP]
            props["temp"] = round(color_util.color_temperature_mired_to_kelvin(mireds))

        if "level" in props:
            if "time" in props:
                await self.send_command(CMD_SET_LEVEL, props["level"], props["time"])
                del props["time"]
            elif "hue" in props:
                arg = json.dumps(
                    {
                        "hue": props["hue"],
                        "saturation": props["sat"],
                        "level": props["level"],
                    }
                )
                await self.send_command(CMD_SET_COLOR, arg)
                del props["hue"]
                del props["sat"]
            else:
                await self.send_command(CMD_SET_LEVEL, props["level"])

            del props["level"]
        else:
            await self.send_command(CMD_ON)

        if "hue" in props:
            arg = json.dumps({"hue": props["hue"], "saturation": props["sat"]})
            await self.send_command(CMD_SET_COLOR, arg)
            del props["hue"]
            del props["sat"]

        if "temp" in props:
            await self.send_command(CMD_SET_COLOR_TEMP, props["temp"])

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the light."""
        _LOGGER.debug(f"Turning off {self.name}")
        await self.send_command("off")


LIGHT_CAPABILITIES = (CAP_COLOR_TEMP, CAP_COLOR_CONTROL, CAP_LIGHT)

# Ideally this would be multi-lingual
MATCH_LIGHT = re.compile(
    r".*\b(light|lamp|chandelier|sconce|luminaire|lumière|candelabra|candle|lantern)s?\b.*",
    re.IGNORECASE,
)


def is_light(device: Device) -> bool:
    """Return True if device looks like a light."""
    if any(cap in device.capabilities for cap in LIGHT_CAPABILITIES):
        return True
    if CAP_SWITCH in device.capabilities and MATCH_LIGHT.match(device.name):
        return True
    if CAP_SWITCH_LEVEL in device.capabilities and not is_cover(device):
        return True

    return False


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: EntityAdder,
) -> None:
    """Initialize light devices."""
    await create_and_add_entities(
        hass, entry, async_add_entities, "light", HubitatLight, is_light
    )
