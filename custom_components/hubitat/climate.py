"""Support for Hubitat thermostats."""

import math
from enum import StrEnum
from logging import getLogger
from typing import TYPE_CHECKING, Any, Literal, Unpack, cast, override

from custom_components.hubitat.const import TEMP_C, TEMP_F
from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from homeassistant.components.climate import (
    ClimateEntity,
)
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DEFAULT_MAX_TEMP,
    FAN_AUTO,
    FAN_ON,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_HOME,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.unit_conversion import TemperatureConverter

from .device import HubitatEntity, HubitatEntityArgs
from .entities import create_and_add_entities
from .hubitatmaker import Device, DeviceCapability, DeviceCommand

_LOGGER = getLogger(__name__)


class ClimateMode(StrEnum):
    AUTO = "auto"
    COOL = "cool"
    DRY = "dry"
    EMERGENCY_HEAT = "emergency heat"
    FAN_ONLY = "fan only"
    HEAT = "heat"
    NEST_ECO = "eco"
    OFF = "off"


class ClimateOpState(StrEnum):
    HEATING = "heating"
    PENDING_COOL = "pending cool"
    PENDING_HEAT = "pending heat"
    VENT_ECONOMIZER = "vent economizer"
    IDLE = "idle"
    COOLING = "cooling"
    FAN_ONLY = "fan only"


class ClimatePresence(StrEnum):
    PRESENT = "present"
    AWAY = "not present"


class ClimateFanMode(StrEnum):
    ON = "on"
    AUTO = "auto"
    CIRCULATE = "circulate"


PRESET_AWAY_AND_ECO = "Away and Eco"

type _TemperatureAttr = Literal[
    "temperature_unit",
    "current_temperature",
    "target_temperature",
    "target_temperature_high",
    "target_temperature_low",
]

# Home Assistant 2026.11 renamed the climate temperature attributes (for example,
# _attr_temperature_unit became _attr_native_temperature_unit). Older versions
# only read the original names.
_TEMPERATURE_ATTR_PREFIX = (
    "_attr_native_" if hasattr(ClimateEntity, "native_temperature_unit") else "_attr_"
)

# Support a lower minimum temperature than the HA default
DEFAULT_MIN_SETPOINT: dict[str, float] = {
    UnitOfTemperature.CELSIUS: 4.4,
    UnitOfTemperature.FAHRENHEIT: 40.0,
}

HASS_FAN_MODES = [FAN_ON, FAN_AUTO]

# HVAC modes offered when a device doesn't report its supported modes
DEFAULT_HVAC_MODES = [
    HVACMode.AUTO,
    HVACMode.HEAT,
    HVACMode.HEAT_COOL,
    HVACMode.COOL,
    HVACMode.OFF,
]

# HA HVAC modes for each Hubitat thermostat mode. Hubitat's auto mode keeps the
# temperature between the heating and cooling setpoints, so it is offered as
# both AUTO and HEAT_COOL.
_HVAC_MODES_BY_CLIMATE_MODE: dict[str, tuple[HVACMode, ...]] = {
    ClimateMode.AUTO: (HVACMode.AUTO, HVACMode.HEAT_COOL),
    ClimateMode.COOL: (HVACMode.COOL,),
    ClimateMode.EMERGENCY_HEAT: (HVACMode.HEAT,),
    ClimateMode.HEAT: (HVACMode.HEAT,),
    ClimateMode.OFF: (HVACMode.OFF,),
}

# Modes that can only be set with setThermostatMode
_SET_MODE_ONLY_HVAC_MODES: dict[str, tuple[HVACMode, ...]] = {
    ClimateMode.DRY: (HVACMode.DRY,),
    ClimateMode.FAN_ONLY: (HVACMode.FAN_ONLY,),
}

# The Hubitat thermostat mode to set for each HA HVAC mode
_CLIMATE_MODE_BY_HVAC_MODE: dict[str, ClimateMode] = {
    HVACMode.AUTO: ClimateMode.AUTO,
    HVACMode.COOL: ClimateMode.COOL,
    HVACMode.DRY: ClimateMode.DRY,
    HVACMode.FAN_ONLY: ClimateMode.FAN_ONLY,
    HVACMode.HEAT: ClimateMode.HEAT,
    HVACMode.HEAT_COOL: ClimateMode.AUTO,
    HVACMode.OFF: ClimateMode.OFF,
}

# Hubitat thermostat modes that have their own command (auto(), cool(), heat(),
# off()), used when a device has no setThermostatMode command
_CLIMATE_MODE_COMMANDS: dict[str, DeviceCommand] = {
    ClimateMode.AUTO: DeviceCommand.AUTO,
    ClimateMode.COOL: DeviceCommand.COOL,
    ClimateMode.HEAT: DeviceCommand.HEAT,
    ClimateMode.OFF: DeviceCommand.OFF,
}

# Per-mode commands used when a device has no setThermostatFanMode command
_FAN_MODE_COMMANDS: dict[str, DeviceCommand] = {
    ClimateFanMode.AUTO: DeviceCommand.FAN_AUTO,
    ClimateFanMode.CIRCULATE: DeviceCommand.FAN_CIRCULATE,
    ClimateFanMode.ON: DeviceCommand.FAN_ON,
}

HASS_PRESET_MODES = [PRESET_HOME, PRESET_AWAY]
HASS_NEST_PRESET_MODES = [
    PRESET_HOME,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_AWAY_AND_ECO,
]


_device_attrs = (
    DeviceAttribute.COOLING_SETPOINT,
    DeviceAttribute.FAN_MODE,
    DeviceAttribute.HEATING_SETPOINT,
    DeviceAttribute.HUMIDITY,
    DeviceAttribute.MAX_SETPOINT,
    DeviceAttribute.MIN_SETPOINT,
    DeviceAttribute.SETPOINT_STEP,
    DeviceAttribute.THERMOSTAT_MODE,
    DeviceAttribute.NEST_MODE,
    DeviceAttribute.OPERATING_STATE,
    DeviceAttribute.PRESENCE,
    DeviceAttribute.TEMP,
    DeviceAttribute.TEMP_UNIT,
)


class HubitatThermostat(ClimateEntity, HubitatEntity):
    """Representation of a Hubitat switch."""

    _attr_supported_features: ClimateEntityFeature
    _attr_min_temp: float
    _attr_max_temp: float
    _temperature_unit: str

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        HubitatEntity.__init__(self, **kwargs)
        ClimateEntity.__init__(self)

        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.FAN_MODE
        )
        self._attr_precision: float = PRECISION_TENTHS
        self._attr_unique_id: str | None = f"{super().unique_id}::climate"

        if hasattr(ClimateEntityFeature, "TURN_OFF"):
            self._attr_supported_features |= ClimateEntityFeature.TURN_OFF
            self._enable_turn_on_off_backwards_compatibility: bool = False

        self.load_state()

    @override
    def load_state(self):
        # The temperature unit must be loaded before the setpoint range
        self._temperature_unit = self._get_temperature_unit()
        self._set_temperature_attr("temperature_unit", self._temperature_unit)
        # In 2025.4.1 this is int | None, in 2025.10.1+ it's float | None
        # We use float | None which works at runtime in both versions
        self._attr_current_humidity: float | None = self._get_current_humidity()
        self._set_temperature_attr(
            "current_temperature", self._get_current_temperature()
        )
        fan_modes = self._get_supported_fan_modes()
        self._attr_fan_modes: list[str] | None = (
            list(HASS_FAN_MODES) if fan_modes is None else fan_modes
        )
        self._attr_fan_mode: str | None = self._get_fan_mode(fan_modes)
        if self._attr_fan_modes:
            self._attr_supported_features |= ClimateEntityFeature.FAN_MODE
        else:
            self._attr_supported_features &= ~ClimateEntityFeature.FAN_MODE
        self._attr_hvac_modes: list[HVACMode] = self._get_hvac_modes()
        self._attr_hvac_mode: HVACMode | None = self._get_hvac_mode()
        self._attr_hvac_action: HVACAction | None = self._get_hvac_action()
        self._attr_preset_mode: str | None = self._get_preset_mode()
        self._attr_preset_modes: list[str] | None = self._get_preset_modes()
        self._set_temperature_attr("target_temperature", self._get_target_temperature())
        self._set_temperature_attr(
            "target_temperature_high", self._get_target_temperature_high()
        )
        self._set_temperature_attr(
            "target_temperature_low", self._get_target_temperature_low()
        )
        (self._attr_min_temp, self._attr_max_temp) = self._get_setpoint_range()
        self._attr_target_temperature_step: float | None = self._get_setpoint_step()

    def _set_temperature_attr(
        self, name: _TemperatureAttr, value: str | float | None
    ) -> None:
        """Set a temperature attribute under this Home Assistant version's name.

        The attribute is set dynamically because the older names are Final
        deprecation aliases in Home Assistant 2026.11, so they can't be assigned
        in code that type checks against it.
        """
        setattr(self, f"{_TEMPERATURE_ATTR_PREFIX}{name}", value)

    def _get_current_humidity(self) -> float | None:
        humidity = self.get_int_attr(DeviceAttribute.HUMIDITY)
        return float(humidity) if humidity is not None else None

    def _get_current_temperature(self) -> float | None:
        return self.get_float_attr(DeviceAttribute.TEMP)

    def _get_supported_fan_modes(self) -> list[str] | None:
        """Return the fan modes the device reports, if it reports them.

        Without a setThermostatFanMode command, only modes that have their own
        command (fanAuto, fanCirculate, fanOn) can be set, so other modes are
        left out.
        """
        modes = self._get_mode_list_attr(DeviceAttribute.SUPPORTED_FAN_MODES)
        if modes is None or self._has_command(DeviceCommand.SET_FAN_MODE):
            return modes
        return [m for m in modes if m.lower() in _FAN_MODE_COMMANDS]

    def _get_fan_mode(self, supported: list[str] | None) -> str | None:
        """Return the current fan mode.

        When the device reports its fan modes, the matching reported mode is
        returned. Otherwise circulate is shown as on.
        """
        mode = self.get_str_attr(DeviceAttribute.FAN_MODE)
        if mode is None:
            return None
        mode = mode.strip()
        if supported is not None:
            return next((m for m in supported if m.lower() == mode.lower()), None)
        mode = mode.lower()
        if mode == ClimateFanMode.CIRCULATE or mode == ClimateFanMode.ON:
            return FAN_ON
        if mode == ClimateFanMode.AUTO:
            return FAN_AUTO
        return None

    def _get_hvac_modes(self) -> list[HVACMode]:
        """Return the HVAC modes for the modes the device reports.

        The default modes are used if the device doesn't report its modes or
        reports none that map to HVAC modes, since a thermostat needs at least
        one mode.
        """
        modes = self._get_mode_list_attr(DeviceAttribute.SUPPORTED_MODES)
        if modes is None:
            return list(DEFAULT_HVAC_MODES)
        mode_map = dict(_HVAC_MODES_BY_CLIMATE_MODE)
        if self._has_command(DeviceCommand.SET_THERMOSTAT_MODE):
            mode_map.update(_SET_MODE_ONLY_HVAC_MODES)
        hvac_modes: list[HVACMode] = []
        for mode in modes:
            for hvac_mode in mode_map.get(mode.lower(), ()):
                if hvac_mode not in hvac_modes:
                    hvac_modes.append(hvac_mode)
        if not hvac_modes:
            _LOGGER.debug("No supported thermostat modes for %s: %s", self.name, modes)
            return list(DEFAULT_HVAC_MODES)
        return hvac_modes

    def _get_hvac_mode(self) -> HVACMode | None:
        """Return hvac operation ie. heat, cool mode.

        An unrecognized mode is shown as auto, as long as the thermostat
        offers auto. Otherwise, and for a mode the thermostat doesn't offer,
        the mode is unknown.
        """
        mode = self.get_str_attr(DeviceAttribute.THERMOSTAT_MODE)
        mode = mode.strip().lower() if mode else None
        hvac_mode = HVACMode.AUTO
        if mode == ClimateMode.OFF:
            hvac_mode = HVACMode.OFF
        elif mode == ClimateMode.HEAT or mode == ClimateMode.EMERGENCY_HEAT:
            hvac_mode = HVACMode.HEAT
        elif mode == ClimateMode.COOL:
            hvac_mode = HVACMode.COOL
        elif mode == ClimateMode.DRY:
            hvac_mode = HVACMode.DRY
        elif mode == ClimateMode.FAN_ONLY:
            hvac_mode = HVACMode.FAN_ONLY
        return hvac_mode if hvac_mode in self._attr_hvac_modes else None

    def _get_mode_list_attr(self, attr: DeviceAttribute) -> list[str] | None:
        """Return the modes listed by a supported modes attribute.

        Modes keep the case the driver reports, since they're sent back to
        the driver. Duplicates (ignoring case) and non-string items are
        dropped. None is returned for a missing or unreadable value.
        """
        try:
            items = self.get_list_attr(attr)
        except ValueError:
            _LOGGER.debug(
                "Ignoring invalid %s for %s: %s",
                attr,
                self.name,
                self.get_str_attr(attr),
            )
            return None
        if items is None:
            return None
        modes: list[str] = []
        seen: set[str] = set()
        for item in items:
            if not isinstance(item, str):
                continue
            mode = item.strip()
            if mode and mode.lower() not in seen:
                seen.add(mode.lower())
                modes.append(mode)
        return modes

    def _has_command(self, command: DeviceCommand) -> bool:
        """Return True if the device supports a command."""
        return command in self._device.commands

    def _get_hvac_action(self) -> HVACAction | None:
        """Return the current running hvac operation if supported."""
        opstate = self.get_str_attr(DeviceAttribute.OPERATING_STATE)
        if opstate == ClimateOpState.PENDING_HEAT or opstate == ClimateOpState.HEATING:
            return HVACAction.HEATING
        if opstate == ClimateOpState.PENDING_COOL or opstate == ClimateOpState.COOLING:
            return HVACAction.COOLING
        if opstate == ClimateOpState.FAN_ONLY:
            return HVACAction.FAN
        if opstate == ClimateOpState.IDLE:
            return HVACAction.IDLE
        return None

    def _get_preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., home, away, temp."""
        nest_mode = self.get_str_attr(DeviceAttribute.NEST_MODE)
        presence = self.get_str_attr(DeviceAttribute.PRESENCE)
        if nest_mode == ClimateMode.NEST_ECO:
            if presence == ClimatePresence.AWAY:
                return PRESET_AWAY_AND_ECO
            return PRESET_ECO
        if presence == ClimatePresence.AWAY:
            return PRESET_AWAY
        return PRESET_HOME

    def _get_preset_modes(self) -> list[str] | None:
        """Return a list of available preset modes."""
        nest_mode = self.get_str_attr(DeviceAttribute.NEST_MODE)
        if nest_mode is not None:
            return HASS_NEST_PRESET_MODES
        return HASS_PRESET_MODES

    def _get_target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if self.hvac_mode == HVACMode.HEAT:
            return self.get_float_attr(DeviceAttribute.HEATING_SETPOINT)
        if self.hvac_mode == HVACMode.COOL:
            return self.get_float_attr(DeviceAttribute.COOLING_SETPOINT)
        return None

    def _get_target_temperature_high(self) -> float | None:
        """Return the highbound target temperature we try to reach."""
        if self.hvac_mode == HVACMode.HEAT_COOL or self.hvac_mode == HVACMode.AUTO:
            return self.get_float_attr(DeviceAttribute.COOLING_SETPOINT)
        return None

    def _get_target_temperature_low(self) -> float | None:
        """Return the lowbound target temperature we try to reach."""
        if self.hvac_mode == HVACMode.HEAT_COOL or self.hvac_mode == HVACMode.AUTO:
            return self.get_float_attr(DeviceAttribute.HEATING_SETPOINT)
        return None

    def _get_setpoint_range(self) -> tuple[float, float]:
        """Return the supported (min, max) setpoint in the entity's unit.

        Drivers may report a device's setpoint limits with minSetpoint and
        maxSetpoint attributes. A missing or invalid limit uses its default
        value. If the resulting range is invalid, the default range is used.
        """
        unit = self._temperature_unit
        default_min = DEFAULT_MIN_SETPOINT.get(
            unit, DEFAULT_MIN_SETPOINT[UnitOfTemperature.CELSIUS]
        )
        default_max = TemperatureConverter.convert(
            DEFAULT_MAX_TEMP, UnitOfTemperature.CELSIUS, unit
        )
        low = self._get_setpoint_attr(DeviceAttribute.MIN_SETPOINT)
        high = self._get_setpoint_attr(DeviceAttribute.MAX_SETPOINT)
        low = default_min if low is None else low
        high = default_max if high is None else high
        if low >= high:
            _LOGGER.debug(
                "Ignoring invalid setpoint range for %s: [%s, %s]",
                self.name,
                low,
                high,
            )
            return default_min, default_max
        return low, high

    def _get_setpoint_step(self) -> float | None:
        """Return the setpoint step reported by a setpointStep attribute."""
        step = self._get_setpoint_attr(DeviceAttribute.SETPOINT_STEP, interval=True)
        if step is None:
            return None
        if step <= 0 or step > self._attr_max_temp - self._attr_min_temp:
            _LOGGER.debug("Ignoring invalid setpoint step for %s: %s", self.name, step)
            return None
        return step

    def _get_setpoint_attr(
        self, attr: DeviceAttribute, interval: bool = False
    ) -> float | None:
        """Return a finite setpoint attribute value in the entity's unit.

        Values with a temperature unit are converted to the entity's unit;
        values without one are assumed to already be in it.
        """
        try:
            value = self.get_float_attr(attr)
        except (TypeError, ValueError) as e:
            _LOGGER.debug("Ignoring invalid %s for %s: %s", attr, self.name, e)
            return None
        if value is None:
            return None
        if not math.isfinite(value):
            _LOGGER.debug("Ignoring invalid %s for %s: %s", attr, self.name, value)
            return None
        unit = _to_temperature_unit(self._device.attributes[attr].unit)
        if unit is not None and unit != self._temperature_unit:
            convert = (
                TemperatureConverter.convert_interval
                if interval
                else TemperatureConverter.convert
            )
            value = convert(value, unit, self._temperature_unit)
        return value

    def _get_temperature_unit(self) -> str:
        """Return the unit of measurement used by the platform."""
        unit = _to_temperature_unit(self.get_str_attr(DeviceAttribute.TEMP_UNIT))
        return unit or self._hub.temperature_unit

    @property
    @override
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return _device_attrs

    @override
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode.

        setThermostatFanMode is used when the device supports it, since
        per-mode commands may conflict with other capabilities.
        """
        if self._has_command(DeviceCommand.SET_FAN_MODE):
            await self.send_command(DeviceCommand.SET_FAN_MODE, fan_mode)
        elif fan_mode.lower() in _FAN_MODE_COMMANDS:
            await self.send_command(_FAN_MODE_COMMANDS[fan_mode.lower()])
        else:
            _LOGGER.warning("%s can't set fan mode %s", self.name, fan_mode)

    @override
    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode.

        setThermostatMode is used when the device supports it, since a
        per-mode command like off() may do something else on some devices
        (for example, turning off a Thermostat Controller).
        """
        mode = _CLIMATE_MODE_BY_HVAC_MODE.get(hvac_mode)
        if mode is None:
            _LOGGER.warning("%s can't set HVAC mode %s", self.name, hvac_mode)
        elif self._has_command(DeviceCommand.SET_THERMOSTAT_MODE):
            await self.send_command(DeviceCommand.SET_THERMOSTAT_MODE, mode)
        elif mode in _CLIMATE_MODE_COMMANDS:
            await self.send_command(_CLIMATE_MODE_COMMANDS[mode])
        else:
            _LOGGER.warning("%s can't set HVAC mode %s", self.name, hvac_mode)

    @override
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == PRESET_AWAY:
            await self.send_command(DeviceCommand.AWAY)
        if preset_mode == PRESET_HOME:
            await self.send_command(DeviceCommand.PRESENT)
        if preset_mode == PRESET_ECO:
            await self.send_command(DeviceCommand.ECO)
        if preset_mode == PRESET_AWAY_AND_ECO:
            await self.send_command(DeviceCommand.AWAY)
            await self.send_command(DeviceCommand.ECO)

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        # The entity's mode only updates when the hub reports the change, so
        # use a requested mode directly when choosing setpoints
        hvac_mode = cast(HVACMode | None, kwargs.get(ATTR_HVAC_MODE))
        if hvac_mode is not None:
            await self.async_set_hvac_mode(hvac_mode)
        else:
            hvac_mode = self.hvac_mode

        if hvac_mode == HVACMode.HEAT_COOL or hvac_mode == HVACMode.AUTO:
            temp_low = cast(float | None, kwargs.get(ATTR_TARGET_TEMP_LOW))
            temp_high = cast(float | None, kwargs.get(ATTR_TARGET_TEMP_HIGH))
            if temp_low is not None:
                await self.send_command(DeviceCommand.SET_HEATING_SETPOINT, temp_low)
            if temp_high is not None:
                await self.send_command(DeviceCommand.SET_COOLING_SETPOINT, temp_high)
        else:
            temp = cast(float | None, kwargs.get(ATTR_TEMPERATURE))
            if temp is not None:
                if hvac_mode == HVACMode.COOL:
                    await self.send_command(DeviceCommand.SET_COOLING_SETPOINT, temp)
                elif hvac_mode == HVACMode.HEAT:
                    await self.send_command(DeviceCommand.SET_HEATING_SETPOINT, temp)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the thermostat."""
        await self.send_command(DeviceCommand.OFF)


def _to_temperature_unit(unit: str | None) -> UnitOfTemperature | None:
    """Return the HA temperature unit for a Hubitat unit like "F" or "°F"."""
    unit = unit.removeprefix("°").upper() if unit else None
    if unit == TEMP_F:
        return UnitOfTemperature.FAHRENHEIT
    if unit == TEMP_C:
        return UnitOfTemperature.CELSIUS
    return None


def is_thermostat(device: Device, _overrides: dict[str, str] | None = None) -> bool:
    """Return True if device looks like a thermostat."""
    return DeviceCapability.THERMOSTAT in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize thermostat devices."""
    _ = create_and_add_entities(
        hass,
        entry,
        async_add_entities,
        "climate",
        HubitatThermostat,
        is_thermostat,
    )


if TYPE_CHECKING:
    from .hub import DEVICE_TYPECHECK, HUB_TYPECHECK

    test_alarm = HubitatThermostat(
        hub=HUB_TYPECHECK,
        device=DEVICE_TYPECHECK,
    )
