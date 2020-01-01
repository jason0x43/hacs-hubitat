"""Support for Hubitat lights."""

from logging import getLogger
import re

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

from .const import DOMAIN
from .device import HubitatDevice
from .hubitat import (
    CAP_COLOR_CONTROL,
    CAP_COLOR_TEMP,
    CAP_SWITCH,
    CAP_SWITCH_LEVEL,
    CMD_ON,
    CMD_SET_COLOR,
    CMD_SET_COLOR_TEMP,
    CMD_SET_HUE,
    CMD_SET_LEVEL,
    CMD_SET_SAT,
    HubitatHub,
)

_LOGGER = getLogger(__name__)


class HubitatLight(HubitatDevice, Light):
    """Representation of a Hubitat light."""

    @property
    def brightness(self):
        """Return the level of this light."""
        return int(255 * int(self._get_attr("level")) / 100)

    @property
    def hs_color(self):
        """Return the hue and saturation color value [float, float]."""
        hue = int(self._get_attr("hue"))
        sat = int(self._get_attr("saturation"))
        hass_hue = 360 * hue / 100
        return [hass_hue, sat]

    @property
    def color_temp(self):
        """Return the CT color value in mireds."""
        temp = int(self._get_attr("colorTemperature"))
        mireds = color_util.color_temperature_kelvin_to_mired(temp)
        return mireds

    @property
    def is_on(self):
        """Return True if the light is on."""
        return self._get_attr("switch") == "on"

    @property
    def supported_features(self):
        """Return supported feature flags."""
        features = 0
        caps = self._device["capabilities"]

        if CAP_COLOR_CONTROL in caps:
            features |= SUPPORT_COLOR
        if CAP_COLOR_TEMP in caps:
            features |= SUPPORT_COLOR_TEMP
        if CAP_SWITCH_LEVEL in caps:
            features |= SUPPORT_BRIGHTNESS

        return features

    def supports_feature(self, feature):
        """Return True if light supports a given feature."""
        return self.supported_features & feature != 0

    async def async_turn_on(self, **kwargs):
        """Turn on the light."""
        _LOGGER.debug(f"Turning on {self.name} with {kwargs}")

        props = {}

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
            props["temp"] = color_util.color_temperature_mired_to_kelvin(mireds)

        if "level" in props:
            if "time" in props:
                await self._send_command(CMD_SET_LEVEL, props["level"], props["time"])
                del props["time"]
            elif "hue" in props:
                await self._send_command(
                    CMD_SET_COLOR, props["hue"], props["sat"], props["level"]
                )
                del props["hue"]
                del props["sat"]
            else:
                await self._send_command(CMD_SET_LEVEL, props["level"])

            del props["level"]
        else:
            await self._send_command(CMD_ON)

        if "hue" in props:
            await self._send_command(CMD_SET_HUE, props["hue"])
            await self._send_command(CMD_SET_SAT, props["sat"])
            del props["hue"]
            del props["sat"]

        if "temp" in props:
            await self._send_command(CMD_SET_COLOR_TEMP, props["temp"])

    async def async_turn_off(self, **kwargs):
        """Turn off the light."""
        _LOGGER.debug(f"Turning off {self.name}")
        await self._send_command("off")


LIGHT_CAPABILITIES = (CAP_COLOR_TEMP, CAP_COLOR_CONTROL)
POSSIBLE_LIGHT_CAPABILITIES = (CAP_SWITCH, CAP_SWITCH_LEVEL)
MATCH_LIGHT = re.compile(r".*\b(light|lamp|chandelier)s?\b.*", re.IGNORECASE)


def _is_light(device):
    """Return True if device looks like a light."""
    if any(cap in device["capabilities"] for cap in LIGHT_CAPABILITIES):
        return True
    if any(
        cap in device["capabilities"] for cap in POSSIBLE_LIGHT_CAPABILITIES
    ) and MATCH_LIGHT.match(device["label"]):
        return True
    return False


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities,
):
    """Initialize light devices."""
    hub: HubitatHub = hass.data[DOMAIN][entry.entry_id].hub
    lights = [HubitatLight(hub=hub, device=d) for d in hub.devices if _is_light(d)]
    async_add_entities(lights)
    _LOGGER.debug(f"Added entities for lights: {lights}")
