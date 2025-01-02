"""Support for Hubitat fans."""

from logging import getLogger
from math import modf
from typing import TYPE_CHECKING, Any, Unpack, override

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import ordered_list_item_to_percentage

from .device import HubitatEntity, HubitatEntityArgs
from .entities import create_and_add_entities
from .hubitatmaker import (
    DEFAULT_FAN_SPEEDS,
    Device,
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
    DeviceState,
)

_LOGGER = getLogger(__name__)

_device_attrs = (
    DeviceAttribute.SWITCH,
    DeviceAttribute.SPEED,
)

_speeds = {}


class HubitatFan(HubitatEntity, FanEntity):
    """Representation of a Hubitat fan."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a Hubitat fan."""
        HubitatEntity.__init__(self, **kwargs)
        FanEntity.__init__(self)
        self._attr_supported_features: FanEntityFeature = FanEntityFeature.SET_SPEED  # pyright: ignore[reportIncompatibleVariableOverride]

        # Enable TURN_ON and TURN_OFF when used with a supporting version of
        # HomeAssistant
        if "TURN_ON" in FanEntityFeature.__members__:
            self._attr_supported_features |= (
                FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF  # type: ignore
            )
            self._enable_turn_on_off_backwards_compatibility: bool = False

        self._attr_unique_id: str | None = f"{super().unique_id}::fan"
        self.load_state()

    @override
    def load_state(self):
        """Load the state of the fan."""
        self._attr_is_on: bool | None = self._get_is_on()
        self._attr_percentage: int | None = self._get_percentage()
        self._attr_preset_mode: str | None = self._get_preset_mode()
        self._attr_preset_modes: list[str] | None = self._get_preset_modes()
        self._attr_speed_count: int = self._get_speed_count()

    def _get_is_on(self) -> bool:
        """Return true if the entity is on."""
        if DeviceCapability.SWITCH in self._device.capabilities:
            return self.get_str_attr(DeviceAttribute.SWITCH) == DeviceState.ON
        return self.get_str_attr(DeviceAttribute.SPEED) != DeviceState.OFF

    def _get_percentage(self) -> int | None:
        """Return the current speed as a percentage."""
        speed = self.get_str_attr(DeviceAttribute.SPEED)
        _LOGGER.debug("hubitat speed: %s", speed)

        if speed is None or speed == "off":
            _LOGGER.debug("returning None")
            return None

        if speed == "auto" or speed == "on":
            _LOGGER.debug("returning 100")
            return 100

        try:
            pct = ordered_list_item_to_percentage(self.speeds, speed)
            _LOGGER.debug(f"returning {pct}%")
            return pct
        except Exception as e:
            _LOGGER.warning(f"Error getting speed pct from reported speeds: {e}")

            try:
                pct = ordered_list_item_to_percentage(DEFAULT_FAN_SPEEDS, speed)
                _LOGGER.debug(f"returning {pct}%")
                return pct
            except Exception as ex:
                _LOGGER.warning(f"Error getting speed pct from default speeds: {ex}")
                return None

    def _get_preset_mode(self) -> str | None:
        """Return the current preset mode"""
        if self.get_str_attr(DeviceAttribute.SPEED) == "auto":
            return "auto"
        return None

    def _get_preset_modes(self) -> list[str] | None:
        """Return a list of available preset modes."""
        if "auto" in self.speeds_and_modes:
            return ["auto"]
        return None

    def _get_speed_count(self) -> int:
        """Return the number of speeds supported by this fan."""
        # Hubitat speeds include 'on', 'off', and 'auto'
        return len(self.speeds)

    @property
    @override
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return _device_attrs

    @property
    def speeds(self) -> list[str]:
        """Return the list of speeds for this fan."""
        speeds = [s for s in self.speeds_and_modes if s not in ["auto", "on", "off"]]
        return speeds

    @property
    def speeds_and_modes(self) -> list[str]:
        """Return the list of speeds and modes for this fan.

        Home Assistant speeds are values that map directly to percentage speeds
        (e.g., low/medium/high or one/two/three). Hubitat also includes
        on/off/auto in its speed list.
        """
        return (
            self.get_list_attr(DeviceAttribute.SUPPORTED_FAN_SPEEDS)
            or DEFAULT_FAN_SPEEDS
        )

    @override
    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,  # pyright: ignore[reportAny]
    ) -> None:
        """Turn on the switch."""
        _LOGGER.debug(
            "Turning on %s with percent [%s] or preset[ %s]",
            self.name,
            percentage,
            preset_mode,
        )
        if preset_mode in self.speeds_and_modes:
            await self.send_command(DeviceCommand.SET_SPEED, preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        elif DeviceCapability.SWITCH in self._device.capabilities:
            await self.send_command(DeviceCommand.ON)
        else:
            await self.send_command(DeviceCommand.SET_SPEED, DeviceState.ON)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:  # pyright: ignore[reportAny]
        """Turn off the switch."""
        _LOGGER.debug("Turning off %s", self.name)
        if DeviceCapability.SWITCH in self._device.capabilities:
            await self.send_command(DeviceCommand.OFF)
        else:
            await self.send_command(DeviceCommand.SET_SPEED, DeviceState.OFF)

    @override
    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan."""
        _LOGGER.debug("setting percentage to %d", percentage)
        if percentage == 0:
            await self.send_command(DeviceCommand.SET_SPEED, DeviceState.OFF)
        else:
            step = self.percentage_step
            [stepFrac, stepInt] = modf(percentage / step)
            idx = int(stepInt)
            if stepFrac >= 0.5:
                idx += 1
            if idx == 0:
                await self.send_command(DeviceCommand.SET_SPEED, DeviceState.OFF)
            else:
                await self.send_command(DeviceCommand.SET_SPEED, self.speeds[idx - 1])


def is_fan(device: Device, overrides: dict[str, str] | None = None) -> bool:
    """Return True if device looks like a fan."""
    if overrides and device.id in overrides and overrides[device.id] != "fan":
        return False
    return DeviceCapability.FAN_CONTROL in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Initialize fan devices."""
    _ = create_and_add_entities(
        hass, entry, async_add_entities, "fan", HubitatFan, is_fan
    )


if TYPE_CHECKING:
    from .hub import DEVICE_TYPECHECK, HUB_TYPECHECK

    test_alarm = HubitatFan(
        hub=HUB_TYPECHECK,
        device=DEVICE_TYPECHECK,
    )
