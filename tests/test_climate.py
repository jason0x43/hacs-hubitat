# pyright: reportAny=false

from typing import Any
from unittest.mock import Mock

from custom_components.hubitat.climate import HubitatThermostat
from custom_components.hubitat.hubitatmaker.const import (
    DeviceAttribute,
    DeviceCapability,
)
from custom_components.hubitat.hubitatmaker.types import Attribute
from homeassistant.components.climate.const import HVACAction, HVACMode
from homeassistant.const import UnitOfTemperature


def create_thermostat_device(**kwargs: Any) -> Mock:
    """Helper to create a mock thermostat device."""
    default_attrs = {
        DeviceAttribute.TEMP: Attribute(
            {
                "name": DeviceAttribute.TEMP,
                "currentValue": "72",
                "dataType": "NUMBER",
                "unit": None,
            }
        ),
        DeviceAttribute.THERMOSTAT_MODE: Attribute(
            {
                "name": DeviceAttribute.THERMOSTAT_MODE,
                "currentValue": "auto",
                "dataType": "STRING",
                "unit": None,
            }
        ),
        DeviceAttribute.HEATING_SETPOINT: Attribute(
            {
                "name": DeviceAttribute.HEATING_SETPOINT,
                "currentValue": "68",
                "dataType": "NUMBER",
                "unit": None,
            }
        ),
        DeviceAttribute.COOLING_SETPOINT: Attribute(
            {
                "name": DeviceAttribute.COOLING_SETPOINT,
                "currentValue": "76",
                "dataType": "NUMBER",
                "unit": None,
            }
        ),
        DeviceAttribute.TEMP_UNIT: Attribute(
            {
                "name": DeviceAttribute.TEMP_UNIT,
                "currentValue": "F",
                "dataType": "STRING",
                "unit": None,
            }
        ),
    }
    default_attrs.update(kwargs.get("attributes", {}))

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Thermostat",
        label="Test Thermostat",
        attributes=default_attrs,
        capabilities={DeviceCapability.THERMOSTAT},
    )
    return device


def test_thermostat_init():
    """Test that a thermostat can be initialized."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = create_thermostat_device()

    thermostat = HubitatThermostat(hub=hub, device=device)

    assert thermostat.current_temperature == 72.0
    assert thermostat.hvac_mode == HVACMode.AUTO


def test_thermostat_temperature_unit():
    """Test that thermostat reports correct temperature unit."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = create_thermostat_device()

    thermostat = HubitatThermostat(hub=hub, device=device)

    assert thermostat.temperature_unit == UnitOfTemperature.FAHRENHEIT


def test_thermostat_celsius():
    """Test that thermostat works with Celsius."""
    hub = Mock()
    hub.configure_mock(token="test-token", temperature_unit=UnitOfTemperature.CELSIUS)

    device = create_thermostat_device(
        attributes={
            DeviceAttribute.TEMP_UNIT: Attribute(
                {
                    "name": DeviceAttribute.TEMP_UNIT,
                    "currentValue": "C",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        }
    )

    thermostat = HubitatThermostat(hub=hub, device=device)

    assert thermostat.temperature_unit == UnitOfTemperature.CELSIUS


def test_thermostat_heat_mode():
    """Test that thermostat correctly reports heat mode."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = create_thermostat_device(
        attributes={
            DeviceAttribute.THERMOSTAT_MODE: Attribute(
                {
                    "name": DeviceAttribute.THERMOSTAT_MODE,
                    "currentValue": "heat",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        }
    )

    thermostat = HubitatThermostat(hub=hub, device=device)

    assert thermostat.hvac_mode == HVACMode.HEAT
    assert thermostat.target_temperature == 68.0
    assert thermostat.target_temperature_high is None
    assert thermostat.target_temperature_low is None


def test_thermostat_cool_mode():
    """Test that thermostat correctly reports cool mode."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = create_thermostat_device(
        attributes={
            DeviceAttribute.THERMOSTAT_MODE: Attribute(
                {
                    "name": DeviceAttribute.THERMOSTAT_MODE,
                    "currentValue": "cool",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        }
    )

    thermostat = HubitatThermostat(hub=hub, device=device)

    assert thermostat.hvac_mode == HVACMode.COOL
    assert thermostat.target_temperature == 76.0


def test_thermostat_off_mode():
    """Test that thermostat correctly reports off mode."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = create_thermostat_device(
        attributes={
            DeviceAttribute.THERMOSTAT_MODE: Attribute(
                {
                    "name": DeviceAttribute.THERMOSTAT_MODE,
                    "currentValue": "off",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        }
    )

    thermostat = HubitatThermostat(hub=hub, device=device)

    assert thermostat.hvac_mode == HVACMode.OFF


def test_thermostat_auto_mode_temperatures():
    """Test that thermostat reports correct temps in auto mode."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = create_thermostat_device()

    thermostat = HubitatThermostat(hub=hub, device=device)

    assert thermostat.hvac_mode == HVACMode.AUTO
    assert thermostat.target_temperature is None
    assert thermostat.target_temperature_low == 68.0
    assert thermostat.target_temperature_high == 76.0


def test_thermostat_hvac_action_heating():
    """Test that thermostat reports heating action."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = create_thermostat_device(
        attributes={
            DeviceAttribute.OPERATING_STATE: Attribute(
                {
                    "name": DeviceAttribute.OPERATING_STATE,
                    "currentValue": "heating",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        }
    )

    thermostat = HubitatThermostat(hub=hub, device=device)

    assert thermostat.hvac_action == HVACAction.HEATING


def test_thermostat_hvac_action_cooling():
    """Test that thermostat reports cooling action."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = create_thermostat_device(
        attributes={
            DeviceAttribute.OPERATING_STATE: Attribute(
                {
                    "name": DeviceAttribute.OPERATING_STATE,
                    "currentValue": "cooling",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        }
    )

    thermostat = HubitatThermostat(hub=hub, device=device)

    assert thermostat.hvac_action == HVACAction.COOLING


def test_thermostat_hvac_action_idle():
    """Test that thermostat reports idle action."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = create_thermostat_device(
        attributes={
            DeviceAttribute.OPERATING_STATE: Attribute(
                {
                    "name": DeviceAttribute.OPERATING_STATE,
                    "currentValue": "idle",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        }
    )

    thermostat = HubitatThermostat(hub=hub, device=device)

    assert thermostat.hvac_action == HVACAction.IDLE


def test_thermostat_humidity():
    """Test that thermostat reports humidity."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = create_thermostat_device(
        attributes={
            DeviceAttribute.HUMIDITY: Attribute(
                {
                    "name": DeviceAttribute.HUMIDITY,
                    "currentValue": "45",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
        }
    )

    thermostat = HubitatThermostat(hub=hub, device=device)

    assert thermostat.current_humidity == 45.0


def test_thermostat_fan_mode():
    """Test that thermostat reports fan mode."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = create_thermostat_device(
        attributes={
            DeviceAttribute.FAN_MODE: Attribute(
                {
                    "name": DeviceAttribute.FAN_MODE,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        }
    )

    thermostat = HubitatThermostat(hub=hub, device=device)

    assert thermostat.fan_mode == "on"
