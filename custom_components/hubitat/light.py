"""Support for Hubitat lights."""

import json
import re
from logging import getLogger
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

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
from .hubitatmaker import (
    ColorMode,
    Device,
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
)
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

_device_attrs = (
    DeviceAttribute.COLOR_MODE,
    DeviceAttribute.COLOR_NAME,
    DeviceAttribute.COLOR_TEMP,
    DeviceAttribute.HUE,
    DeviceAttribute.LEVEL,
    DeviceAttribute.SATURATION,
    DeviceAttribute.SWITCH,
)


class HubitatLight(HubitatEntity, LightEntity):
    """Representation of a Hubitat light."""

    @property
    def device_attrs(self) -> Optional[Sequence[str]]:
        """Return this entity's associated attributes"""
        return _device_attrs

    @property
    def color_mode(self) -> Optional[str]:
        """Return this light's color mode."""
        he_color_mode = self.get_str_attr(DeviceAttribute.COLOR_MODE)
        if he_color_mode == ColorMode.CT:
            return COLOR_MODE_COLOR_TEMP
        if he_color_mode == ColorMode.RGB:
            return COLOR_MODE_HS
        return None

    @property
    def color_name(self) -> Optional[str]:
        """Return the name of this light's current color."""
        return self.get_str_attr(DeviceAttribute.COLOR_NAME)

    @property
    def brightness(self) -> Optional[int]:
        """Return the level of this light."""
        level = self.get_int_attr(DeviceAttribute.LEVEL)
        if level is None:
            return None
        return int(255 * level / 100)

    @property
    def color_temp(self) -> Optional[float]:
        """Return the CT color value in mireds."""
        mode = self.color_mode
        if mode and mode != COLOR_MODE_COLOR_TEMP:
            return None

        temp = self.get_int_attr(DeviceAttribute.COLOR_TEMP)
        if temp is None:
            return None

        return color_util.color_temperature_kelvin_to_mired(temp)

    @property
    def hs_color(self) -> Optional[Tuple[float, float]]:
        """Return the hue and saturation color value [float, float]."""
        mode = self.color_mode
        if mode and mode != COLOR_MODE_HS:
            return None

        hue = self.get_float_attr(DeviceAttribute.HUE)
        sat = self.get_float_attr(DeviceAttribute.SATURATION)
        if hue is None or sat is None:
            return None

        hass_hue = 360 * hue / 100
        return (hass_hue, sat)

    @property
    def is_on(self) -> bool:
        """Return True if the light is on."""
        return self.get_str_attr(DeviceAttribute.SWITCH) == "on"

    @property
    def supported_color_modes(self) -> set:
        caps = self._device.capabilities
        supported_modes = set()

        if DeviceCapability.COLOR_CONTROL in caps:
            supported_modes.add(COLOR_MODE_HS)
        if DeviceCapability.COLOR_TEMP in caps:
            supported_modes.add(COLOR_MODE_COLOR_TEMP)

        if DeviceCapability.SWITCH_LEVEL in caps and not supported_modes:
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
        if DeviceCapability.COLOR_CONTROL in caps:
            features |= SUPPORT_COLOR
        # deprecated, replaced by color modes
        if DeviceCapability.COLOR_TEMP in caps:
            features |= SUPPORT_COLOR_TEMP
        # deprecated, replaced by color modes
        if DeviceCapability.SWITCH_LEVEL in caps:
            features |= SUPPORT_BRIGHTNESS

        if DeviceCommand.FLASH in cmds:
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
                await self.send_command(
                    DeviceCommand.SET_LEVEL, props["level"], props["time"]
                )
                del props["time"]
            elif "hue" in props:
                arg = json.dumps(
                    {
                        "hue": props["hue"],
                        "saturation": props["sat"],
                        "level": props["level"],
                    }
                )
                await self.send_command(DeviceCommand.SET_COLOR, arg)
                del props["hue"]
                del props["sat"]
            else:
                await self.send_command(DeviceCommand.SET_LEVEL, props["level"])

            del props["level"]
        else:
            await self.send_command(DeviceCommand.ON)

        if "hue" in props:
            data = {
                "hue": props["hue"],
                "saturation": props["sat"],
            }
            level = self.get_int_attr(DeviceAttribute.LEVEL)
            if isinstance(level, int):
                data["level"] = level

            arg = json.dumps(data)
            await self.send_command(DeviceCommand.SET_COLOR, arg)
            del props["hue"]
            del props["sat"]

        if "temp" in props:
            await self.send_command(DeviceCommand.SET_COLOR_TEMP, props["temp"])

        if ATTR_FLASH in kwargs and self.supports_feature(SUPPORT_FLASH):
            await self.send_command(DeviceCommand.FLASH)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        _LOGGER.debug(f"Turning off {self.name}")
        await self.send_command("off")


LIGHT_CAPABILITIES = (DeviceCapability.COLOR_TEMP, DeviceCapability.COLOR_CONTROL)

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
    if DeviceCapability.SWITCH in device.capabilities and MATCH_LIGHT.search(
        device.label
    ):
        return True
    if DeviceCapability.LIGHT in device.capabilities:
        return True

    # A Cover may also have a SwitchLevel capability that can be used to set
    # the height of the cover. Fans may have SwitchLevel, but it seems to only
    # apply to light switches in that case.
    if DeviceCapability.SWITCH_LEVEL in device.capabilities and not is_cover(device):
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
    create_and_add_entities(
        hass, config_entry, async_add_entities, "light", HubitatLight, is_light
    )
