"""Support for Hubitat lights."""

import json
import re
from logging import getLogger
from typing import TYPE_CHECKING, Any, Unpack, cast, override

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_FLASH,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)

try:
    from homeassistant.components.light.const import (  # pyright: ignore[reportMissingImports]
        DEFAULT_MAX_KELVIN,  # pyright: ignore[reportUnknownVariableType]
        DEFAULT_MIN_KELVIN,  # pyright: ignore[reportUnknownVariableType]
    )
except Exception:
    DEFAULT_MIN_KELVIN = 2000  # pyright: ignore[reportConstantRedefinition]
    DEFAULT_MAX_KELVIN = 6535  # pyright: ignore[reportConstantRedefinition]

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .cover import is_cover
from .device import HubitatEntity, HubitatEntityArgs
from .entities import create_and_add_entities
from .hubitatmaker import (
    Device,
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
    HubitatColorMode,
)

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

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a Hubitat light."""
        HubitatEntity.__init__(self, **kwargs)
        LightEntity.__init__(self)
        self._attr_unique_id: str | None = f"{super().unique_id}::light"
        self._attr_supported_color_modes: set[ColorMode] | set[str] | None = (
            self._get_supported_color_modes()
        )
        self._attr_supported_features: LightEntityFeature = (  # pyright: ignore[reportIncompatibleVariableOverride]
            self._get_supported_features()
        )
        self._attr_min_color_temp_kelvin: int | None = DEFAULT_MIN_KELVIN
        self._attr_max_color_temp_kelvin: int | None = DEFAULT_MAX_KELVIN
        self.load_state()

    @override
    def load_state(self):
        self._attr_color_mode: ColorMode | str | None = self._get_color_mode()
        self._attr_brightness: int | None = self._get_brightness()
        self._attr_color_temp_kelvin: int | None = self._get_color_temp_kelvin()
        self._attr_hs_color: tuple[float, float] | None = self._get_hs_color()
        self._attr_is_on: bool | None = self._get_is_on()

    def _get_color_mode(self) -> ColorMode | str | None:
        """Return this light's color mode.

        Hubitat directly reports CT and RGB color modes. Otherwise we can infer
        that a light supports brightness if it has the SwitchLevel capability.
        It must at the very least support on/off to be a light.
        """
        he_color_mode = self.get_str_attr(DeviceAttribute.COLOR_MODE)

        if he_color_mode == HubitatColorMode.CT:
            return ColorMode.COLOR_TEMP

        if he_color_mode == HubitatColorMode.RGB:
            return ColorMode.HS

        if DeviceCapability.COLOR_CONTROL in self._device.capabilities:
            return ColorMode.HS

        if DeviceCapability.COLOR_TEMP in self._device.capabilities:
            return ColorMode.COLOR_TEMP

        if DeviceCapability.SWITCH_LEVEL in self._device.capabilities:
            return ColorMode.BRIGHTNESS

        return ColorMode.ONOFF

    def _get_brightness(self) -> int | None:
        """Return the level of this light."""
        level = self.get_int_attr(DeviceAttribute.LEVEL)
        if level is None:
            return None
        return round(255 * level / 100)

    def _get_color_temp_kelvin(self) -> int | None:
        """Return the CT color value in Kelvin."""
        mode = self.color_mode
        if mode and mode != ColorMode.COLOR_TEMP:
            return None

        temp = self.get_int_attr(DeviceAttribute.COLOR_TEMP)
        if temp is None:
            return None

        return temp

    def _get_hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation color value [float, float]."""
        mode = self.color_mode
        if mode and mode != ColorMode.HS:
            return None

        hue = self.get_float_attr(DeviceAttribute.HUE)
        sat = self.get_float_attr(DeviceAttribute.SATURATION)
        if hue is None or sat is None:
            return None

        hass_hue = 360 * hue / 100
        return (hass_hue, sat)

    def _get_is_on(self) -> bool:
        """Return True if the light is on."""
        return self.get_str_attr(DeviceAttribute.SWITCH) == "on"

    def _get_supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        caps = self._device.capabilities
        supported_modes: set[ColorMode] = set()

        if DeviceCapability.COLOR_CONTROL in caps:
            supported_modes.add(ColorMode.HS)
        if DeviceCapability.COLOR_TEMP in caps:
            supported_modes.add(ColorMode.COLOR_TEMP)

        if DeviceCapability.SWITCH_LEVEL in caps and not supported_modes:
            supported_modes.add(ColorMode.BRIGHTNESS)

        if not supported_modes:
            supported_modes.add(ColorMode.ONOFF)

        return supported_modes

    def _get_supported_features(self) -> LightEntityFeature:
        """Return supported feature flags."""
        cmds = self._device.commands

        # All lights support the Switch capability, which supports transition
        features = LightEntityFeature.TRANSITION

        if DeviceCommand.FLASH in cmds:
            features |= LightEntityFeature.FLASH

        return features

    @property
    @override
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return _device_attrs

    @property
    def color_name(self) -> str | None:
        """Return the name of this light's current color."""
        return self.get_str_attr(DeviceAttribute.COLOR_NAME)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:  # pyright: ignore[reportAny]
        """Turn on the light."""
        _LOGGER.debug(f"Turning on {self.name} with {kwargs}")

        props: dict[str, int | str] = {}
        caps = self._device.capabilities

        if ATTR_BRIGHTNESS in kwargs and DeviceCapability.SWITCH_LEVEL in caps:
            props["level"] = round(100 * cast(float, kwargs[ATTR_BRIGHTNESS]) / 255)

        if ATTR_TRANSITION in kwargs:
            props["time"] = kwargs[ATTR_TRANSITION]

        if ATTR_HS_COLOR in kwargs and DeviceCapability.COLOR_CONTROL in caps:
            # Hubitat hue is from 0 - 100
            props["hue"] = round(100 * cast(float, kwargs[ATTR_HS_COLOR][0]) / 360)
            props["sat"] = kwargs[ATTR_HS_COLOR][1]

        if ATTR_COLOR_TEMP_KELVIN in kwargs and DeviceCapability.COLOR_TEMP in caps:
            props["temp"] = kwargs[ATTR_COLOR_TEMP_KELVIN]

        _LOGGER.debug(f"Light {self.name} turn-on props: {props}")

        if "time" in props:
            if "hue" in props:
                arg = {
                    "hue": props["hue"],
                    "saturation": props["sat"],
                }
                if "level" in props:
                    arg["level"] = props["level"]
                await self.send_command(DeviceCommand.SET_COLOR, json.dumps(arg))
            elif "temp" in props:
                level: int | None = None
                if "level" in props:
                    level = cast(int, props["level"])
                else:
                    brightness = self._get_brightness()
                    if brightness is not None:
                        level = round(100 * brightness / 255)

                if level is not None:
                    await self.send_command(
                        DeviceCommand.SET_COLOR_TEMP,
                        props["temp"],
                        level,
                        props["time"],
                    )
                else:
                    await self.send_command(
                        DeviceCommand.SET_COLOR_TEMP,
                        props["temp"],
                    )
            elif "level" in props:
                await self.send_command(
                    DeviceCommand.SET_LEVEL, props["level"], props["time"]
                )
            else:
                await self.send_command(DeviceCommand.ON)
        elif "hue" in props:
            arg = {
                "hue": props["hue"],
                "saturation": props["sat"],
            }
            if "level" in props:
                arg["level"] = props["level"]
            await self.send_command(DeviceCommand.SET_COLOR, json.dumps(arg))
        elif "temp" in props:
            if "level" in props:
                await self.send_command(
                    DeviceCommand.SET_COLOR_TEMP,
                    props["temp"],
                    props["level"],
                )
            else:
                await self.send_command(
                    DeviceCommand.SET_COLOR_TEMP,
                    props["temp"],
                )
        elif "level" in props:
            await self.send_command(DeviceCommand.SET_LEVEL, props["level"])
        else:
            await self.send_command(DeviceCommand.ON)

        if ATTR_FLASH in kwargs and LightEntityFeature.FLASH in self.supported_features:
            await self.send_command(DeviceCommand.FLASH)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:  # pyright: ignore[reportAny]
        """Turn off the light."""
        _LOGGER.debug(f"Turning off {self.name}")
        if ATTR_TRANSITION in kwargs:
            time = cast(float, kwargs[ATTR_TRANSITION])
            await self.send_command(DeviceCommand.SET_LEVEL, 0, time)
        else:
            await self.send_command(DeviceCommand.OFF)


LIGHT_CAPABILITIES = (DeviceCapability.COLOR_TEMP, DeviceCapability.COLOR_CONTROL)

# Ideally this would be multi-lingual
MATCH_LIGHT = re.compile(
    r".*\b(light|lamp|chandelier|sconce|luminaire|lumière|candelabra|candle|lantern)s?\b.*",
    re.IGNORECASE,
)


def is_light(device: Device, overrides: dict[str, str] | None = None) -> bool:
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
    device: Device, _overrides: dict[str, str] | None = None
) -> bool:
    """Return True if the device has light-specific capabilities."""
    return any(cap in device.capabilities for cap in LIGHT_CAPABILITIES)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize light devices."""
    _ = create_and_add_entities(
        hass, config_entry, async_add_entities, "light", HubitatLight, is_light
    )


if TYPE_CHECKING:
    from .hub import DEVICE_TYPECHECK, HUB_TYPECHECK

    test_alarm = HubitatLight(
        hub=HUB_TYPECHECK,
        device=DEVICE_TYPECHECK,
    )
