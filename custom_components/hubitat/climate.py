"""Support for Hubitat thermostats."""

from logging import getLogger
from typing import List, Optional

from hubitatmaker import (
    CAP_THERMOSTAT,
    CMD_AUTO,
    CMD_AWAY,
    CMD_COOL,
    CMD_ECO,
    CMD_FAN_AUTO,
    CMD_FAN_ON,
    CMD_HEAT,
    CMD_OFF,
    CMD_PRESENT,
    CMD_SET_COOLING_SETPOINT,
    CMD_SET_HEATING_SETPOINT,
    Device,
)

from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_FAN,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    FAN_AUTO,
    FAN_ON,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_HOME,
    SUPPORT_FAN_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT
from homeassistant.core import HomeAssistant

from .device import HubitatEntity
from .entities import create_and_add_entities
from .types import EntityAdder

_LOGGER = getLogger(__name__)

ATTR_COOLING_SETPOINT = "coolingSetpoint"
ATTR_FAN_MODE = "thermostatFanMode"
ATTR_HEATING_SETPOINT = "heatingSetpoint"
ATTR_HUMIDITY = "humidity"
ATTR_MODE = "thermostatMode"
ATTR_NEST_MODE = "nestThermostatMode"
ATTR_NEST_SUPPORTED_MODES = "supportedNestThermostatModes"
ATTR_OPERATING_STATE = "thermostatOperatingState"
ATTR_PRESENCE = "presence"
ATTR_SUPPORTED_FAN_MODES = "supportedThermostatFanModes"
ATTR_SUPPORTED_MODES = "supportedThermostatModes"
ATTR_TEMP = "temperature"
ATTR_TEMP_UNIT = "temperatureUnit"

MODE_AUTO = "auto"
MODE_COOL = "cool"
MODE_EMERGENCY_HEAT = "emergency heat"
MODE_HEAT = "heat"
MODE_NEST_ECO = "eco"
MODE_OFF = "off"
HASS_MODES = [HVAC_MODE_HEAT, HVAC_MODE_HEAT_COOL, HVAC_MODE_COOL, HVAC_MODE_OFF]

OPSTATE_HEATING = "heating"
OPSTATE_PENDING_COOL = "pending cool"
OPSTATE_PENDING_HEAT = "pending heat"
OPSTATE_VENT_ECONOMIZER = "vent economizer"
OPSTATE_IDLE = "idle"
OPSTATE_COOLING = "cooling"
OPSTATE_FAN_ONLY = "fan only"
HASS_ACTIONS = [
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_FAN,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
]

UNIT_FAHRENHEIT = "F"
UNIT_CELSIUS = "C"

PRESENCE_PRESENT = "present"
PRESENCE_AWAY = "not present"
PRESET_AWAY_AND_ECO = "Away and Eco"
HASS_PRESET_MODES = [PRESET_HOME, PRESET_AWAY]
HASS_NEST_PRESET_MODES = [PRESET_HOME, PRESET_AWAY, PRESET_ECO, PRESET_AWAY_AND_ECO]

FAN_MODE_ON = "on"
FAN_MODE_AUTO = "auto"
FAN_MODE_CIRCULATE = "circulate"
HASS_FAN_MODES = [FAN_ON, FAN_AUTO]


class HubitatThermostat(HubitatEntity, ClimateDevice):
    """Representation of a Hubitat switch."""

    @property
    def current_humidity(self) -> Optional[int]:
        """Return the current humidity."""
        return self.get_int_attr(ATTR_HUMIDITY)

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        return self.get_float_attr(ATTR_TEMP)

    @property
    def fan_mode(self) -> Optional[str]:
        """Return the fan setting."""
        mode = self.get_str_attr(ATTR_FAN_MODE)
        if mode == FAN_MODE_CIRCULATE or mode == FAN_MODE_ON:
            return FAN_ON
        if mode == FAN_MODE_AUTO:
            return FAN_AUTO
        return None

    @property
    def fan_modes(self) -> Optional[List[str]]:
        """Return the list of available fan modes."""
        return HASS_FAN_MODES

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        mode = self.get_str_attr(ATTR_MODE)
        if mode == MODE_OFF:
            return HVAC_MODE_OFF
        if mode == MODE_HEAT or mode == MODE_EMERGENCY_HEAT:
            return HVAC_MODE_HEAT
        if mode == MODE_COOL:
            return HVAC_MODE_COOL
        return HVAC_MODE_AUTO

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes."""
        return HASS_MODES

    @property
    def hvac_action(self) -> Optional[str]:
        """Return the current running hvac operation if supported."""
        opstate = self.get_str_attr(ATTR_OPERATING_STATE)
        if opstate == OPSTATE_PENDING_HEAT or opstate == OPSTATE_HEATING:
            return CURRENT_HVAC_HEAT
        if opstate == OPSTATE_PENDING_COOL or opstate == OPSTATE_COOLING:
            return CURRENT_HVAC_COOL
        if opstate == OPSTATE_FAN_ONLY:
            return CURRENT_HVAC_FAN
        if opstate == OPSTATE_IDLE:
            return CURRENT_HVAC_IDLE
        return None

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp."""
        nest_mode = self.get_str_attr(ATTR_NEST_MODE)
        presence = self.get_str_attr(ATTR_PRESENCE)
        if nest_mode == MODE_NEST_ECO:
            if presence == PRESENCE_AWAY:
                return PRESET_AWAY_AND_ECO
            return PRESET_ECO
        if presence == PRESENCE_AWAY:
            return PRESET_AWAY
        return PRESET_HOME

    @property
    def preset_modes(self) -> Optional[List[str]]:
        """Return a list of available preset modes."""
        nest_mode = self.get_str_attr(ATTR_NEST_MODE)
        if nest_mode is not None:
            return HASS_NEST_PRESET_MODES
        return HASS_PRESET_MODES

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return (
            SUPPORT_TARGET_TEMPERATURE
            | SUPPORT_PRESET_MODE
            | SUPPORT_TARGET_TEMPERATURE_RANGE
            | SUPPORT_FAN_MODE
        )

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_HEAT:
            return self.get_float_attr(ATTR_HEATING_SETPOINT)
        if self.hvac_mode == HVAC_MODE_COOL:
            return self.get_float_attr(ATTR_COOLING_SETPOINT)
        return None

    @property
    def target_temperature_high(self) -> Optional[float]:
        """Return the highbound target temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_HEAT_COOL or self.hvac_mode == HVAC_MODE_AUTO:
            return self.get_float_attr(ATTR_HEATING_SETPOINT)
        return None

    @property
    def target_temperature_low(self) -> Optional[float]:
        """Return the lowbound target temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_HEAT_COOL or self.hvac_mode == HVAC_MODE_AUTO:
            return self.get_float_attr(ATTR_COOLING_SETPOINT)
        return None

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement used by the platform."""
        unit = self.get_str_attr(ATTR_TEMP_UNIT)
        if unit == UNIT_FAHRENHEIT:
            return TEMP_FAHRENHEIT
        if unit == UNIT_CELSIUS:
            return TEMP_CELSIUS

        # Guess the scale based on the current reported temperature
        temp = self.current_temperature
        if temp is None or temp > 50:
            return TEMP_FAHRENHEIT
        return TEMP_CELSIUS

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if fan_mode == FAN_ON:
            await self.send_command(CMD_FAN_ON)
        elif fan_mode == FAN_AUTO:
            await self.send_command(CMD_FAN_AUTO)

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_COOL:
            await self.send_command(CMD_COOL)
        elif hvac_mode == HVAC_MODE_HEAT:
            await self.send_command(CMD_HEAT)
        elif hvac_mode == HVAC_MODE_HEAT_COOL:
            await self.send_command(CMD_AUTO)
        elif hvac_mode == HVAC_MODE_OFF:
            await self.send_command(CMD_OFF)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == PRESET_AWAY:
            await self.send_command(CMD_AWAY)
        if preset_mode == PRESET_HOME:
            await self.send_command(CMD_PRESENT)
        if preset_mode == PRESET_ECO:
            await self.send_command(CMD_ECO)
        if preset_mode == PRESET_AWAY_AND_ECO:
            await self.send_command(CMD_AWAY)
            await self.send_command(CMD_ECO)

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if self.hvac_mode == HVAC_MODE_HEAT_COOL:
            temp_low = kwargs.get(ATTR_TARGET_TEMP_LOW)
            temp_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
            if temp_low is not None:
                await self.send_command(CMD_SET_COOLING_SETPOINT, temp_low)
            if temp_high is not None:
                await self.send_command(CMD_SET_HEATING_SETPOINT, temp_high)
        else:
            temp = kwargs.get(ATTR_TEMPERATURE)
            if temp is not None:
                if self.hvac_mode == HVAC_MODE_COOL:
                    await self.send_command(CMD_SET_COOLING_SETPOINT, temp)
                elif self.hvac_mode == HVAC_MODE_HEAT:
                    await self.send_command(CMD_SET_HEATING_SETPOINT, temp)


def is_thermostat(device: Device) -> bool:
    """Return True if device looks like a thermostat."""
    return CAP_THERMOSTAT in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: EntityAdder,
) -> None:
    """Initialize thermostat devices."""
    await create_and_add_entities(
        hass, entry, async_add_entities, "climate", HubitatThermostat, is_thermostat
    )
