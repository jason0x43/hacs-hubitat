"""Support for Hubitat lights."""

import json
from logging import getLogger
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from hubitatmaker import (
    ATTR_COLOR_MODE as HE_ATTR_COLOR_MODE,
    ATTR_COLOR_NAME as HE_ATTR_COLOR_NAME,
    ATTR_COLOR_TEMP as HE_ATTR_COLOR_TEMP,
    ATTR_HUE as HE_ATTR_HUE,
    ATTR_LEVEL as HE_ATTR_LEVEL,
    ATTR_SATURATION as HE_ATTR_SATURATION,
    ATTR_SWITCH as HE_ATTR_SWITCH,
    CAP_COLOR_CONTROL,
    CAP_COLOR_TEMP,
    CAP_LIGHT,
    CAP_SWITCH,
    CAP_SWITCH_LEVEL,
    CMD_FLASH,
    CMD_ON,
    CMD_SET_COLOR,
    CMD_SET_COLOR_TEMP,
    CMD_SET_LEVEL,
    COLOR_MODE_CT as HE_COLOR_MODE_CT,
    COLOR_MODE_RGB as HE_COLOR_MODE_RGB,
    Device,
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_FLASH,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    SUPPORT_FLASH,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import color as color_util

from .cover import is_cover
from .device import HubitatEntity
from .entities import create_and_add_entities
from .types import EntityAdder

try:
    from homeassistant.components.light import (
        COLOR_MODE_BRIGHTNESS,
        COLOR_MODE_COLOR_TEMP,
        COLOR_MODE_HS,
        COLOR_MODE_ONOFF,
    )
except ImportError:
    COLOR_MODE_BRIGHTNESS = "brightness"
    COLOR_MODE_COLOR_TEMP = "color_temp"
    COLOR_MODE_HS = "hs"
    COLOR_MODE_ONOFF = "onoff"


_LOGGER = getLogger(__name__)


class HubitatLight(HubitatEntity, LightEntity):
    """Representation of a Hubitat light."""

    @property
    def color_mode(self) -> Optional[str]:
        """Return this light's color mode."""
        he_color_mode = self.get_str_attr(HE_ATTR_COLOR_MODE)
        if he_color_mode == HE_COLOR_MODE_CT:
            return COLOR_MODE_COLOR_TEMP
        if he_color_mode == HE_COLOR_MODE_RGB:
            return COLOR_MODE_HS
        return None

    @property
    def color_name(self) -> Optional[str]:
        """Return the name of this light's current color."""
        return self.get_str_attr(HE_ATTR_COLOR_NAME)

    @property
    def brightness(self) -> Optional[int]:
        """Return the level of this light."""
        level = self.get_int_attr(HE_ATTR_LEVEL)
        if level is None:
            return None
        return int(255 * level / 100)

    @property
    def color_temp(self) -> Optional[float]:
        """Return the CT color value in mireds."""
        mode = self.color_mode
        if mode and mode != COLOR_MODE_COLOR_TEMP:
            return None

        temp = self.get_int_attr(HE_ATTR_COLOR_TEMP)
        if temp is None:
            return None

        return color_util.color_temperature_kelvin_to_mired(temp)

    @property
    def hs_color(self) -> Optional[Tuple[float, float]]:
        """Return the hue and saturation color value [float, float]."""
        mode = self.color_mode
        if mode and mode != COLOR_MODE_HS:
            return None

        hue = self.get_float_attr(HE_ATTR_HUE)
        sat = self.get_float_attr(HE_ATTR_SATURATION)
        if hue is None or sat is None:
            return None

        hass_hue = 360 * hue / 100
        return (hass_hue, sat)

    @property
    def is_on(self) -> bool:
        """Return True if the light is on."""
        return self.get_str_attr(HE_ATTR_SWITCH) == "on"

    @property
    def supported_color_modes(self) -> set:
        caps = self._device.capabilities
        supported_modes = set()

        if CAP_COLOR_CONTROL in caps:
            supported_modes.add(COLOR_MODE_HS)
        if CAP_COLOR_TEMP in caps:
            supported_modes.add(COLOR_MODE_COLOR_TEMP)

        if CAP_SWITCH_LEVEL in caps and not supported_modes:
            supported_modes.add(COLOR_MODE_BRIGHTNESS)

        if not supported_modes:
            supported_modes.add(COLOR_MODE_ONOFF)

        return supported_modes

    @property
    def supported_features(self) -> int:
        """Return supported feature flags."""
        features = 0
        caps = self._device.capabilities
        cmds = self._device.commands

        # deprecated, replaced by color modes
        if CAP_COLOR_CONTROL in caps:
            features |= SUPPORT_COLOR
        # deprecated, replaced by color modes
        if CAP_COLOR_TEMP in caps:
            features |= SUPPORT_COLOR_TEMP
        # deprecated, replaced by color modes
        if CAP_SWITCH_LEVEL in caps:
            features |= SUPPORT_BRIGHTNESS

        if CMD_FLASH in cmds:
            features |= SUPPORT_FLASH

        return features

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this light."""
        return f"{super().unique_id}::light"

    @property
    def old_unique_ids(self) -> List[str]:
        """Return the legacy unique ID for this light."""
        old_ids = [super().unique_id]
        old_parent_ids = super().old_unique_ids
        old_ids.extend(old_parent_ids)
        return old_ids

    def supports_feature(self, feature: int) -> bool:
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

        if ATTR_FLASH in kwargs and self.supports_feature(SUPPORT_FLASH):
            await self.send_command(CMD_FLASH)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        _LOGGER.debug(f"Turning off {self.name}")
        await self.send_command("off")


LIGHT_CAPABILITIES = (CAP_COLOR_TEMP, CAP_COLOR_CONTROL, CAP_LIGHT)

# Ideally this would be multi-lingual
MATCH_LIGHT = re.compile(
    r".*\b(light|lamp|chandelier|sconce|luminaire|lumière|candelabra|candle|lantern)s?\b.*",
    re.IGNORECASE,
)


def is_light(device: Device, overrides: Optional[Dict[str, str]] = None) -> bool:
    """Return True if device looks like a light."""
    if overrides and overrides.get(device.id) is not None:
        return overrides[device.id] == "light"

    if is_definitely_light(device):
        return True
    if CAP_SWITCH in device.capabilities and MATCH_LIGHT.search(device.name):
        return True

    # A Cover may also have a SwitchLevel capability that can be used to set
    # the height of the cover. Fans may have SwitchLevel, but it seems to only
    # apply to light switches in that case.
    if CAP_SWITCH_LEVEL in device.capabilities and not is_cover(device):
        return True

    return False


def is_definitely_light(
    device: Device, overrides: Optional[Dict[str, str]] = None
) -> bool:
    """Return True if the device has light-specific capabilities."""
    return any(cap in device.capabilities for cap in LIGHT_CAPABILITIES)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: EntityAdder,
) -> None:
    """Initialize light devices."""
    await create_and_add_entities(
        hass, config_entry, async_add_entities, "light", HubitatLight, is_light
    )
