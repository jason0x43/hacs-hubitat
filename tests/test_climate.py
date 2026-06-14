from typing import Any
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from custom_components.hubitat.climate import (
    PRESET_AWAY_AND_ECO,
    HubitatThermostat,
    async_setup_entry,
    is_thermostat,
)
from custom_components.hubitat.hubitatmaker.const import (
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
)
from custom_components.hubitat.hubitatmaker.types import Attribute
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    FAN_AUTO,
    FAN_ON,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_HOME,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature


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


@pytest.mark.parametrize(
    ("attribute", "value", "property_name", "expected"),
    [
        (DeviceAttribute.FAN_MODE, "auto", "fan_mode", FAN_AUTO),
        (DeviceAttribute.FAN_MODE, "invalid", "fan_mode", None),
        (DeviceAttribute.OPERATING_STATE, "fan only", "hvac_action", HVACAction.FAN),
        (
            DeviceAttribute.OPERATING_STATE,
            "pending heat",
            "hvac_action",
            HVACAction.HEATING,
        ),
        (
            DeviceAttribute.OPERATING_STATE,
            "pending cool",
            "hvac_action",
            HVACAction.COOLING,
        ),
        (DeviceAttribute.OPERATING_STATE, "unknown", "hvac_action", None),
    ],
)
def test_thermostat_additional_states(
    attribute: DeviceAttribute,
    value: str,
    property_name: str,
    expected: str | None,
) -> None:
    hub = Mock(token="token", temperature_unit=UnitOfTemperature.FAHRENHEIT)
    device = create_thermostat_device(
        attributes={
            attribute: Attribute(
                {
                    "name": attribute,
                    "currentValue": value,
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        }
    )
    thermostat = HubitatThermostat(hub=hub, device=device)
    assert getattr(thermostat, property_name) == expected


@pytest.mark.parametrize(
    ("nest_mode", "presence", "expected"),
    [
        ("eco", "not present", PRESET_AWAY_AND_ECO),
        ("eco", "present", PRESET_ECO),
        (None, "not present", PRESET_AWAY),
        (None, "present", PRESET_HOME),
    ],
)
def test_thermostat_preset_states(
    nest_mode: str | None, presence: str, expected: str
) -> None:
    attrs = {
        DeviceAttribute.PRESENCE: Attribute(
            {
                "name": DeviceAttribute.PRESENCE,
                "currentValue": presence,
                "dataType": "STRING",
                "unit": None,
            }
        )
    }
    if nest_mode is not None:
        attrs[DeviceAttribute.NEST_MODE] = Attribute(
            {
                "name": DeviceAttribute.NEST_MODE,
                "currentValue": nest_mode,
                "dataType": "STRING",
                "unit": None,
            }
        )
    thermostat = HubitatThermostat(
        hub=Mock(token="token", temperature_unit=UnitOfTemperature.FAHRENHEIT),
        device=create_thermostat_device(attributes=attrs),
    )
    assert thermostat.preset_mode == expected


def test_thermostat_temperature_unit_fallback_and_device_attrs() -> None:
    thermostat = HubitatThermostat(
        hub=Mock(token="token", temperature_unit=UnitOfTemperature.CELSIUS),
        device=create_thermostat_device(
            attributes={
                DeviceAttribute.TEMP_UNIT: Attribute(
                    {
                        "name": DeviceAttribute.TEMP_UNIT,
                        "currentValue": "unknown",
                        "dataType": "STRING",
                        "unit": None,
                    }
                )
            }
        ),
    )
    assert thermostat.temperature_unit == UnitOfTemperature.CELSIUS
    assert thermostat.device_attrs is not None
    assert DeviceAttribute.TEMP in thermostat.device_attrs


@pytest.mark.asyncio
async def test_thermostat_commands() -> None:
    thermostat = HubitatThermostat(
        hub=Mock(token="token", temperature_unit=UnitOfTemperature.FAHRENHEIT),
        device=create_thermostat_device(),
    )
    thermostat.send_command = AsyncMock()  # type: ignore[method-assign]

    await thermostat.async_set_fan_mode(FAN_ON)
    await thermostat.async_set_fan_mode(FAN_AUTO)
    for mode in (HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO, HVACMode.OFF):
        await thermostat.async_set_hvac_mode(mode)
    for preset in (PRESET_AWAY, PRESET_HOME, PRESET_ECO, PRESET_AWAY_AND_ECO):
        await thermostat.async_set_preset_mode(preset)
    await thermostat.async_set_temperature(
        **{ATTR_TARGET_TEMP_LOW: 65, ATTR_TARGET_TEMP_HIGH: 75}
    )
    thermostat._attr_hvac_mode = HVACMode.COOL
    await thermostat.async_set_temperature(**{ATTR_TEMPERATURE: 74})
    thermostat._attr_hvac_mode = HVACMode.HEAT
    await thermostat.async_set_temperature(**{ATTR_TEMPERATURE: 68})
    await thermostat.async_turn_off()

    thermostat.send_command.assert_has_awaits(
        [
            call(DeviceCommand.FAN_ON),
            call(DeviceCommand.FAN_AUTO),
            call(DeviceCommand.COOL),
            call(DeviceCommand.HEAT),
            call(DeviceCommand.AUTO),
            call(DeviceCommand.OFF),
        ]
    )
    assert thermostat.send_command.await_count == 16


@pytest.mark.asyncio
async def test_thermostat_setup_and_detection() -> None:
    assert is_thermostat(Mock(capabilities={DeviceCapability.THERMOSTAT}))
    assert not is_thermostat(Mock(capabilities=set()))
    with patch("custom_components.hubitat.climate.create_and_add_entities") as create:
        await async_setup_entry(Mock(), Mock(), Mock())
    create.assert_called_once()
