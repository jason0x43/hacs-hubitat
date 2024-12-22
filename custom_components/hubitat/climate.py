"""Support for Hubitat thermostats."""

from enum import StrEnum
from typing import TYPE_CHECKING, Any, Unpack, cast, override

from custom_components.hubitat.const import TEMP_C, TEMP_F
from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from homeassistant.components.climate import (
    ClimateEntity,
)
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
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

from .device import HubitatEntity, HubitatEntityArgs
from .entities import create_and_add_entities
from .hubitatmaker import Device, DeviceCapability, DeviceCommand


class ClimateMode(StrEnum):
    AUTO = "auto"
    COOL = "cool"
    EMERGENCY_HEAT = "emergency heat"
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
HASS_FAN_MODES = [FAN_ON, FAN_AUTO]
HASS_PRESET_MODES = [PRESET_HOME, PRESET_AWAY]
HASS_NEST_PRESET_MODES = [PRESET_HOME, PRESET_AWAY, PRESET_ECO, PRESET_AWAY_AND_ECO]


_device_attrs = (
    DeviceAttribute.COOLING_SETPOINT,
    DeviceAttribute.FAN_MODE,
    DeviceAttribute.HEATING_SETPOINT,
    DeviceAttribute.HUMIDITY,
    DeviceAttribute.THERMOSTAT_MODE,
    DeviceAttribute.NEST_MODE,
    DeviceAttribute.OPERATING_STATE,
    DeviceAttribute.PRESENCE,
    DeviceAttribute.TEMP,
    DeviceAttribute.TEMP_UNIT,
)


class HubitatThermostat(HubitatEntity, ClimateEntity):
    """Representation of a Hubitat switch."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        HubitatEntity.__init__(self, **kwargs)
        ClimateEntity.__init__(self)

        self._attr_hvac_modes: list[HVACMode] = [
            HVACMode.AUTO,
            HVACMode.HEAT,
            HVACMode.HEAT_COOL,
            HVACMode.COOL,
            HVACMode.OFF,
        ]
        self._attr_fan_modes: list[str] | None = HASS_FAN_MODES
        self._attr_supported_features: ClimateEntityFeature = (  # pyright: ignore[reportIncompatibleVariableOverride]
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.FAN_MODE
        )
        self._attr_precision: float = PRECISION_TENTHS
        self._attr_unique_id: str | None = f"{super().unique_id}::climate"

        # Support a lower minimum temperature than the HA default
        self._attr_min_temp: float = 4.4

        if hasattr(ClimateEntityFeature, "TURN_OFF"):
            self._attr_supported_features |= getattr(ClimateEntityFeature, "TURN_OFF")
            self._enable_turn_on_off_backwards_compatibility: bool = False

        self.load_state()

    @override
    def load_state(self):
        self._attr_current_humidity: int | None = self._get_current_humidity()
        self._attr_current_temperature: float | None = self._get_current_temperature()
        self._attr_fan_mode: str | None = self._get_fan_mode()
        self._attr_hvac_mode: HVACMode | None = self._get_hvac_mode()
        self._attr_hvac_action: HVACAction | None = self._get_hvac_action()
        self._attr_preset_mode: str | None = self._get_preset_mode()
        self._attr_preset_modes: list[str] | None = self._get_preset_modes()
        self._attr_target_temperature: float | None = self._get_target_temperature()
        self._attr_target_temperature_high: float | None = (
            self._get_target_temperature_high()
        )
        self._attr_target_temperature_low: float | None = (
            self._get_target_temperature_low()
        )
        self._attr_temperature_unit: str = self._get_temperature_unit()

    def _get_current_humidity(self) -> int | None:
        return self.get_int_attr(DeviceAttribute.HUMIDITY)

    def _get_current_temperature(self) -> float | None:
        return self.get_float_attr(DeviceAttribute.TEMP)

    def _get_fan_mode(self) -> str | None:
        mode = self.get_str_attr(DeviceAttribute.FAN_MODE)
        if mode == ClimateFanMode.CIRCULATE or mode == ClimateFanMode.ON:
            return FAN_ON
        if mode == ClimateFanMode.AUTO:
            return FAN_AUTO
        return None

    def _get_hvac_mode(self) -> HVACMode | None:
        """Return hvac operation ie. heat, cool mode."""
        mode = self.get_str_attr(DeviceAttribute.THERMOSTAT_MODE)
        if mode == ClimateMode.OFF:
            return HVACMode.OFF
        if mode == ClimateMode.HEAT or mode == ClimateMode.EMERGENCY_HEAT:
            return HVACMode.HEAT
        if mode == ClimateMode.COOL:
            return HVACMode.COOL
        return HVACMode.AUTO

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

    def _get_temperature_unit(self) -> str:
        """Return the unit of measurement used by the platform."""
        unit = self.get_str_attr(DeviceAttribute.TEMP_UNIT)
        if unit == TEMP_F:
            return UnitOfTemperature.FAHRENHEIT
        if unit == TEMP_C:
            return UnitOfTemperature.CELSIUS
        return self._hub.temperature_unit

    @property
    @override
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return _device_attrs

    @override
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if fan_mode == FAN_ON:
            await self.send_command(DeviceCommand.FAN_ON)
        elif fan_mode == FAN_AUTO:
            await self.send_command(DeviceCommand.FAN_AUTO)

    @override
    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.COOL:
            await self.send_command(DeviceCommand.COOL)
        elif hvac_mode == HVACMode.HEAT:
            await self.send_command(DeviceCommand.HEAT)
        elif hvac_mode == HVACMode.HEAT_COOL or hvac_mode == HVACMode.AUTO:
            await self.send_command(DeviceCommand.AUTO)
        elif hvac_mode == HVACMode.OFF:
            await self.send_command(DeviceCommand.OFF)

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
    async def async_set_temperature(self, **kwargs: Any) -> None:  # pyright: ignore[reportAny]
        """Set new target temperature."""
        if self.hvac_mode == HVACMode.HEAT_COOL or self.hvac_mode == HVACMode.AUTO:
            temp_low = cast(float | None, kwargs.get(ATTR_TARGET_TEMP_LOW))
            temp_high = cast(float | None, kwargs.get(ATTR_TARGET_TEMP_HIGH))
            if temp_low is not None:
                await self.send_command(DeviceCommand.SET_HEATING_SETPOINT, temp_low)
            if temp_high is not None:
                await self.send_command(DeviceCommand.SET_COOLING_SETPOINT, temp_high)
        else:
            temp = cast(float | None, kwargs.get(ATTR_TEMPERATURE))
            if temp is not None:
                if self.hvac_mode == HVACMode.COOL:
                    await self.send_command(DeviceCommand.SET_COOLING_SETPOINT, temp)
                elif self.hvac_mode == HVACMode.HEAT:
                    await self.send_command(DeviceCommand.SET_HEATING_SETPOINT, temp)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:  # pyright: ignore[reportAny]
        """Turn off the thermostat."""
        await self.send_command("off")


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
        hass, entry, async_add_entities, "climate", HubitatThermostat, is_thermostat
    )


if TYPE_CHECKING:
    from .hub import DEVICE_TYPECHECK, HUB_TYPECHECK

    test_alarm = HubitatThermostat(
        hub=HUB_TYPECHECK,
        device=DEVICE_TYPECHECK,
    )
