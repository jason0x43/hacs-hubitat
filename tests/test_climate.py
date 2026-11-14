from typing import Any
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from custom_components.hubitat.climate import (
    DEFAULT_HVAC_MODES,
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
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
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
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature


def temperature_attr(thermostat: HubitatThermostat, name: str) -> Any:
    """Read a climate temperature property by this Home Assistant version's name.

    Home Assistant 2026.11 renamed these properties with a native_ prefix.
    """
    native_name = f"native_{name}"
    if hasattr(ClimateEntity, native_name):
        return getattr(thermostat, native_name)
    return getattr(thermostat, name)


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
        commands=kwargs.get("commands", []),
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

    assert temperature_attr(thermostat, "current_temperature") == 72.0
    assert thermostat.hvac_mode == HVACMode.AUTO


def test_thermostat_temperature_unit():
    """Test that thermostat reports correct temperature unit."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = create_thermostat_device()

    thermostat = HubitatThermostat(hub=hub, device=device)

    assert (
        temperature_attr(thermostat, "temperature_unit") == UnitOfTemperature.FAHRENHEIT
    )


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

    assert temperature_attr(thermostat, "temperature_unit") == UnitOfTemperature.CELSIUS


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
    assert temperature_attr(thermostat, "target_temperature") == 68.0
    assert temperature_attr(thermostat, "target_temperature_high") is None
    assert temperature_attr(thermostat, "target_temperature_low") is None


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
    assert temperature_attr(thermostat, "target_temperature") == 76.0


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
    assert temperature_attr(thermostat, "target_temperature") is None
    assert temperature_attr(thermostat, "target_temperature_low") == 68.0
    assert temperature_attr(thermostat, "target_temperature_high") == 76.0


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
    assert temperature_attr(thermostat, "temperature_unit") == UnitOfTemperature.CELSIUS
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
async def test_thermostat_set_temperature_with_hvac_mode() -> None:
    thermostat = HubitatThermostat(
        hub=Mock(token="token", temperature_unit=UnitOfTemperature.FAHRENHEIT),
        device=create_thermostat_device(),
    )
    thermostat.send_command = AsyncMock()  # type: ignore[method-assign]

    # Range setpoints are used for a requested auto mode even when the
    # thermostat is currently in heat mode
    thermostat._attr_hvac_mode = HVACMode.HEAT
    await thermostat.async_set_temperature(
        **{
            ATTR_HVAC_MODE: HVACMode.AUTO,
            ATTR_TARGET_TEMP_LOW: 59,
            ATTR_TARGET_TEMP_HIGH: 80,
            ATTR_TEMPERATURE: 79,
        }
    )
    assert thermostat.send_command.await_args_list == [
        call(DeviceCommand.AUTO),
        call(DeviceCommand.SET_HEATING_SETPOINT, 59),
        call(DeviceCommand.SET_COOLING_SETPOINT, 80),
    ]

    thermostat.send_command.reset_mock()
    await thermostat.async_set_temperature(
        **{
            ATTR_HVAC_MODE: HVACMode.HEAT_COOL,
            ATTR_TARGET_TEMP_LOW: 62,
            ATTR_TARGET_TEMP_HIGH: 78,
        }
    )
    assert thermostat.send_command.await_args_list == [
        call(DeviceCommand.AUTO),
        call(DeviceCommand.SET_HEATING_SETPOINT, 62),
        call(DeviceCommand.SET_COOLING_SETPOINT, 78),
    ]

    # A single setpoint follows the requested mode, not the current one
    thermostat._attr_hvac_mode = HVACMode.AUTO
    thermostat.send_command.reset_mock()
    await thermostat.async_set_temperature(
        **{ATTR_HVAC_MODE: HVACMode.COOL, ATTR_TEMPERATURE: 74}
    )
    assert thermostat.send_command.await_args_list == [
        call(DeviceCommand.COOL),
        call(DeviceCommand.SET_COOLING_SETPOINT, 74),
    ]

    thermostat.send_command.reset_mock()
    await thermostat.async_set_temperature(
        **{ATTR_HVAC_MODE: HVACMode.HEAT, ATTR_TEMPERATURE: 68}
    )
    assert thermostat.send_command.await_args_list == [
        call(DeviceCommand.HEAT),
        call(DeviceCommand.SET_HEATING_SETPOINT, 68),
    ]

    # Turning off sends no setpoints
    thermostat.send_command.reset_mock()
    await thermostat.async_set_temperature(
        **{ATTR_HVAC_MODE: HVACMode.OFF, ATTR_TEMPERATURE: 70}
    )
    assert thermostat.send_command.await_args_list == [call(DeviceCommand.OFF)]


@pytest.mark.asyncio
async def test_thermostat_set_temperature_without_hvac_mode() -> None:
    thermostat = HubitatThermostat(
        hub=Mock(token="token", temperature_unit=UnitOfTemperature.FAHRENHEIT),
        device=create_thermostat_device(),
    )
    thermostat.send_command = AsyncMock()  # type: ignore[method-assign]

    # Setpoints follow the current mode and no mode command is sent
    thermostat._attr_hvac_mode = HVACMode.AUTO
    await thermostat.async_set_temperature(
        **{ATTR_TARGET_TEMP_LOW: 65, ATTR_TARGET_TEMP_HIGH: 75, ATTR_TEMPERATURE: 70}
    )
    assert thermostat.send_command.await_args_list == [
        call(DeviceCommand.SET_HEATING_SETPOINT, 65),
        call(DeviceCommand.SET_COOLING_SETPOINT, 75),
    ]

    thermostat._attr_hvac_mode = HVACMode.COOL
    thermostat.send_command.reset_mock()
    await thermostat.async_set_temperature(
        **{ATTR_TARGET_TEMP_LOW: 65, ATTR_TARGET_TEMP_HIGH: 75, ATTR_TEMPERATURE: 74}
    )
    assert thermostat.send_command.await_args_list == [
        call(DeviceCommand.SET_COOLING_SETPOINT, 74)
    ]

    thermostat._attr_hvac_mode = HVACMode.HEAT
    thermostat.send_command.reset_mock()
    await thermostat.async_set_temperature(**{ATTR_TEMPERATURE: 68})
    assert thermostat.send_command.await_args_list == [
        call(DeviceCommand.SET_HEATING_SETPOINT, 68)
    ]

    thermostat._attr_hvac_mode = HVACMode.OFF
    thermostat.send_command.reset_mock()
    await thermostat.async_set_temperature(**{ATTR_TEMPERATURE: 68})
    thermostat.send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_thermostat_setup_and_detection() -> None:
    assert is_thermostat(Mock(capabilities={DeviceCapability.THERMOSTAT}))
    assert not is_thermostat(Mock(capabilities=set()))
    with patch("custom_components.hubitat.climate.create_and_add_entities") as create:
        await async_setup_entry(Mock(), Mock(), Mock())
    create.assert_called_once()


def _thermostat_with_setpoint_attrs(
    unit: str = "F", attr_unit: str | None = None, **values: str
) -> HubitatThermostat:
    """Create a thermostat reporting the given setpoint attributes."""
    attributes = {
        DeviceAttribute.TEMP_UNIT: Attribute(
            {
                "name": DeviceAttribute.TEMP_UNIT,
                "currentValue": unit,
                "dataType": "STRING",
                "unit": None,
            }
        )
    }
    for name, value in values.items():
        attr = DeviceAttribute(name)
        attributes[attr] = Attribute(
            {
                "name": attr,
                "currentValue": value,
                "dataType": "NUMBER",
                "unit": attr_unit,
            }
        )
    return HubitatThermostat(
        hub=Mock(token="token", temperature_unit=UnitOfTemperature.FAHRENHEIT),
        device=create_thermostat_device(attributes=attributes),
    )


def test_thermostat_setpoint_range_default_celsius() -> None:
    """Celsius thermostats default to a 4.4-35 C setpoint range."""
    thermostat = _thermostat_with_setpoint_attrs("C")
    assert thermostat.min_temp == pytest.approx(4.4)
    assert thermostat.max_temp == pytest.approx(35)
    assert thermostat.target_temperature_step is None


def test_thermostat_setpoint_range_default_fahrenheit() -> None:
    """The default range is converted for Fahrenheit thermostats."""
    thermostat = _thermostat_with_setpoint_attrs("F")
    assert thermostat.min_temp == 40
    assert thermostat.max_temp == pytest.approx(95)


def test_thermostat_setpoint_range_reported() -> None:
    """Device-reported setpoint limits and step override the defaults."""
    thermostat = _thermostat_with_setpoint_attrs(
        minSetpoint="41", maxSetpoint="90", setpointStep="0.5"
    )
    assert thermostat.min_temp == 41
    assert thermostat.max_temp == 90
    assert thermostat.target_temperature_step == 0.5


def test_thermostat_setpoint_range_partial() -> None:
    """A missing limit uses its default value."""
    thermostat = _thermostat_with_setpoint_attrs(minSetpoint="41")
    assert thermostat.min_temp == 41
    assert thermostat.max_temp == pytest.approx(95)

    thermostat = _thermostat_with_setpoint_attrs(maxSetpoint="90")
    assert thermostat.min_temp == 40
    assert thermostat.max_temp == 90


@pytest.mark.parametrize(
    "values",
    [
        {"minSetpoint": "90", "maxSetpoint": "41"},
        {"minSetpoint": "70", "maxSetpoint": "70"},
        {"minSetpoint": "abc", "maxSetpoint": "abc"},
        {"minSetpoint": "nan", "maxSetpoint": "1e400"},
        {"maxSetpoint": "30"},
    ],
)
def test_thermostat_setpoint_range_invalid(values: dict[str, str]) -> None:
    """An invalid reported range falls back to the default range."""
    thermostat = _thermostat_with_setpoint_attrs(**values)
    assert thermostat.min_temp == 40
    assert thermostat.max_temp == pytest.approx(95)


@pytest.mark.parametrize("value", ["0", "-1", "abc", "inf", "nan", "100"])
def test_thermostat_setpoint_step_invalid(value: str) -> None:
    """An invalid reported step is ignored."""
    thermostat = _thermostat_with_setpoint_attrs(setpointStep=value)
    assert thermostat.target_temperature_step is None


def test_thermostat_setpoint_range_updates() -> None:
    """Setpoint limits reported after startup are picked up on the next event."""
    thermostat = _thermostat_with_setpoint_attrs(minSetpoint="41", maxSetpoint="90")
    thermostat._device.attributes[DeviceAttribute.MIN_SETPOINT].update_value("45")
    thermostat._device.attributes[DeviceAttribute.MAX_SETPOINT].update_value("85")
    thermostat.load_state()
    assert thermostat.min_temp == 45
    assert thermostat.max_temp == 85


def test_thermostat_setpoint_attrs_are_device_attrs() -> None:
    """Setpoint attributes aren't also exposed as generic sensors."""
    attrs = _thermostat_with_setpoint_attrs().device_attrs
    assert attrs is not None
    assert DeviceAttribute.MIN_SETPOINT in attrs
    assert DeviceAttribute.MAX_SETPOINT in attrs
    assert DeviceAttribute.SETPOINT_STEP in attrs


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"minSetpoint": "41", "maxSetpoint": "abc"}, (41, 95)),
        ({"minSetpoint": "nan", "maxSetpoint": "90"}, (40, 90)),
    ],
)
def test_thermostat_setpoint_range_invalid_limit(
    values: dict[str, str], expected: tuple[float, float]
) -> None:
    """An invalid limit only falls back to its own default."""
    thermostat = _thermostat_with_setpoint_attrs(**values)
    assert (thermostat.min_temp, thermostat.max_temp) == pytest.approx(expected)


def test_thermostat_setpoint_range_reported_celsius() -> None:
    """Reported limits on a Celsius thermostat are used as-is."""
    thermostat = _thermostat_with_setpoint_attrs(
        "C", minSetpoint="5", maxSetpoint="30", setpointStep="0.5"
    )
    assert thermostat.min_temp == 5
    assert thermostat.max_temp == 30
    assert thermostat.target_temperature_step == 0.5


def test_thermostat_setpoint_attribute_unit() -> None:
    """Limits reported with a temperature unit are converted to the entity's."""
    thermostat = _thermostat_with_setpoint_attrs(
        "C", attr_unit="°F", minSetpoint="41", maxSetpoint="86", setpointStep="1.8"
    )
    assert thermostat.min_temp == pytest.approx(5)
    assert thermostat.max_temp == pytest.approx(30)
    assert thermostat.target_temperature_step == pytest.approx(1)


def test_thermostat_setpoint_range_hub_unit_change() -> None:
    """Default limits follow a hub temperature unit change."""
    hub = Mock(token="token", temperature_unit=UnitOfTemperature.FAHRENHEIT)
    device = create_thermostat_device()
    del device.attributes[DeviceAttribute.TEMP_UNIT]
    thermostat = HubitatThermostat(hub=hub, device=device)
    assert thermostat.min_temp == 40
    assert thermostat.max_temp == pytest.approx(95)

    hub.temperature_unit = UnitOfTemperature.CELSIUS
    thermostat.load_state()
    assert temperature_attr(thermostat, "temperature_unit") == UnitOfTemperature.CELSIUS
    assert thermostat.min_temp == pytest.approx(4.4)
    assert thermostat.max_temp == pytest.approx(35)


def _enum_attr(name: DeviceAttribute, value: str) -> Attribute:
    return Attribute(
        {"name": name, "currentValue": value, "dataType": "ENUM", "unit": None}
    )


def _thermostat_with_modes(
    modes: str | None = None,
    fan_modes: str | None = None,
    commands: list[str] | None = None,
    attrs: dict[DeviceAttribute, str] | None = None,
) -> tuple[HubitatThermostat, AsyncMock]:
    """Create a thermostat that reports supported modes and attribute values.

    Returns the thermostat and its mocked send_command.
    """
    values = dict(attrs or {})
    if modes is not None:
        values[DeviceAttribute.SUPPORTED_MODES] = modes
    if fan_modes is not None:
        values[DeviceAttribute.SUPPORTED_FAN_MODES] = fan_modes
    attributes = {name: _enum_attr(name, value) for name, value in values.items()}
    thermostat = HubitatThermostat(
        hub=Mock(token="token", temperature_unit=UnitOfTemperature.FAHRENHEIT),
        device=create_thermostat_device(attributes=attributes, commands=commands or []),
    )
    send_command = AsyncMock()
    thermostat.send_command = send_command  # type: ignore[method-assign]
    return thermostat, send_command


@pytest.mark.asyncio
async def test_thermostat_set_fan_mode_with_set_fan_mode_keeps_case() -> None:
    thermostat, send_command = _thermostat_with_modes(
        fan_modes='["Auto", "Circulate"]', commands=[DeviceCommand.SET_FAN_MODE]
    )
    await thermostat.async_set_fan_mode("Circulate")
    assert send_command.await_args_list == [
        call(DeviceCommand.SET_FAN_MODE, "Circulate")
    ]


@pytest.mark.asyncio
async def test_thermostat_set_unsupported_fan_mode() -> None:
    thermostat, send_command = _thermostat_with_modes()
    await thermostat.async_set_fan_mode("followschedule")
    send_command.assert_not_awaited()


@pytest.mark.parametrize(
    ("modes", "commands", "expected"),
    [
        ("[off, heat]", [], [HVACMode.OFF, HVACMode.HEAT]),
        ('["heat", "emergency heat", "off"]', [], [HVACMode.HEAT, HVACMode.OFF]),
        (
            "[auto, off, heat, emergency heat, cool]",
            [],
            [
                HVACMode.AUTO,
                HVACMode.HEAT_COOL,
                HVACMode.OFF,
                HVACMode.HEAT,
                HVACMode.COOL,
            ],
        ),
        ("[off, cool, dry, fan only]", [], [HVACMode.OFF, HVACMode.COOL]),
        (
            "[off, cool, dry, fan only]",
            [DeviceCommand.SET_THERMOSTAT_MODE],
            [HVACMode.OFF, HVACMode.COOL, HVACMode.DRY, HVACMode.FAN_ONLY],
        ),
        ("[OFF, Heat]", [], [HVACMode.OFF, HVACMode.HEAT]),
        (None, [], DEFAULT_HVAC_MODES),
        ("not a list", [], DEFAULT_HVAC_MODES),
        ('{"mode": "heat"}', [], DEFAULT_HVAC_MODES),
        ("[eco]", [], DEFAULT_HVAC_MODES),
        ("[]", [], DEFAULT_HVAC_MODES),
    ],
)
def test_thermostat_hvac_modes(
    modes: str | None, commands: list[str], expected: list[HVACMode]
) -> None:
    thermostat, _ = _thermostat_with_modes(modes=modes, commands=commands)
    assert thermostat.hvac_modes == expected


def test_thermostat_hvac_modes_update() -> None:
    """Supported modes reported after startup are picked up on the next event."""
    thermostat, _ = _thermostat_with_modes(modes="[off, heat]")
    thermostat._device.attributes[DeviceAttribute.SUPPORTED_MODES].update_value(
        "[off, cool]"
    )
    thermostat.load_state()
    assert thermostat.hvac_modes == [HVACMode.OFF, HVACMode.COOL]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [("dry", HVACMode.DRY), ("fan only", HVACMode.FAN_ONLY)],
)
def test_thermostat_extra_hvac_mode_states(mode: str, expected: HVACMode) -> None:
    thermostat, _ = _thermostat_with_modes(
        modes="[off, dry, fan only]",
        commands=[DeviceCommand.SET_THERMOSTAT_MODE],
        attrs={DeviceAttribute.THERMOSTAT_MODE: mode},
    )
    assert thermostat.hvac_mode == expected


@pytest.mark.parametrize("mode", ["eco", "auto"])
def test_thermostat_hvac_mode_not_offered(mode: str) -> None:
    """A mode the thermostat doesn't offer is reported as unknown."""
    thermostat, _ = _thermostat_with_modes(
        modes="[off, heat, cool, eco]", attrs={DeviceAttribute.THERMOSTAT_MODE: mode}
    )
    assert thermostat.hvac_modes == [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    assert thermostat.hvac_mode is None


def test_thermostat_unknown_hvac_mode_with_default_modes() -> None:
    """Without reported modes, an unrecognized mode is still shown as auto."""
    thermostat, _ = _thermostat_with_modes(
        attrs={DeviceAttribute.THERMOSTAT_MODE: "eco"}
    )
    assert thermostat.hvac_mode == HVACMode.AUTO


def test_thermostat_reported_fan_modes() -> None:
    thermostat, _ = _thermostat_with_modes(
        fan_modes='["circulate"]', attrs={DeviceAttribute.FAN_MODE: "circulate"}
    )
    assert thermostat.fan_modes == ["circulate"]
    assert thermostat.fan_mode == "circulate"


def test_thermostat_reported_fan_mode_unsupported() -> None:
    thermostat, _ = _thermostat_with_modes(
        fan_modes="[auto, on]", attrs={DeviceAttribute.FAN_MODE: "circulate"}
    )
    assert thermostat.fan_modes == ["auto", "on"]
    assert thermostat.fan_mode is None


@pytest.mark.parametrize("fan_modes", [None, "garbage"])
def test_thermostat_default_fan_modes(fan_modes: str | None) -> None:
    thermostat, _ = _thermostat_with_modes(
        fan_modes=fan_modes, attrs={DeviceAttribute.FAN_MODE: "circulate"}
    )
    assert thermostat.fan_modes == [FAN_ON, FAN_AUTO]
    assert thermostat.fan_mode == FAN_ON


def test_thermostat_reported_fan_modes_keep_case() -> None:
    """Fan modes keep the driver's case, since they're sent back to it."""
    thermostat, _ = _thermostat_with_modes(
        fan_modes='["Auto", "On", "auto", "Circulate"]',
        commands=[DeviceCommand.SET_FAN_MODE],
        attrs={DeviceAttribute.FAN_MODE: "circulate"},
    )
    assert thermostat.fan_modes == ["Auto", "On", "Circulate"]
    assert thermostat.fan_mode == "Circulate"


def test_thermostat_reported_fan_modes_without_set_fan_mode() -> None:
    """Without setThermostatFanMode, only modes with a command are offered."""
    thermostat, _ = _thermostat_with_modes(fan_modes="[auto, on, followschedule]")
    assert thermostat.fan_modes == ["auto", "on"]


def test_thermostat_no_fan_modes() -> None:
    """A device that reports no fan modes doesn't support setting one."""
    thermostat, _ = _thermostat_with_modes(fan_modes="[]")
    assert thermostat.fan_modes == []
    assert ClimateEntityFeature.FAN_MODE not in thermostat.supported_features

    thermostat._device.attributes[DeviceAttribute.SUPPORTED_FAN_MODES].update_value(
        "[auto]"
    )
    thermostat.load_state()
    assert thermostat.fan_modes == ["auto"]
    assert ClimateEntityFeature.FAN_MODE in thermostat.supported_features


def test_thermostat_supported_mode_attrs_are_generic_sensors() -> None:
    """Supported mode attributes stay available as generic sensors.

    Claiming them would orphan generic sensors that users have enabled.
    """
    attrs = _thermostat_with_modes()[0].device_attrs
    assert attrs is not None
    assert DeviceAttribute.SUPPORTED_MODES not in attrs
    assert DeviceAttribute.SUPPORTED_FAN_MODES not in attrs


@pytest.mark.asyncio
async def test_thermostat_set_hvac_mode_with_set_thermostat_mode() -> None:
    thermostat, send_command = _thermostat_with_modes(
        commands=[DeviceCommand.SET_THERMOSTAT_MODE, DeviceCommand.OFF]
    )
    for mode in (
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.AUTO,
        HVACMode.HEAT_COOL,
        HVACMode.OFF,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ):
        await thermostat.async_set_hvac_mode(mode)
    await thermostat.async_turn_off()

    assert send_command.await_args_list == [
        call(DeviceCommand.SET_THERMOSTAT_MODE, "cool"),
        call(DeviceCommand.SET_THERMOSTAT_MODE, "heat"),
        call(DeviceCommand.SET_THERMOSTAT_MODE, "auto"),
        call(DeviceCommand.SET_THERMOSTAT_MODE, "auto"),
        call(DeviceCommand.SET_THERMOSTAT_MODE, "off"),
        call(DeviceCommand.SET_THERMOSTAT_MODE, "dry"),
        call(DeviceCommand.SET_THERMOSTAT_MODE, "fan only"),
        call(DeviceCommand.OFF),
    ]


@pytest.mark.asyncio
async def test_thermostat_set_temperature_with_set_thermostat_mode() -> None:
    thermostat, send_command = _thermostat_with_modes(
        commands=[DeviceCommand.SET_THERMOSTAT_MODE]
    )
    await thermostat.async_set_temperature(
        **{ATTR_HVAC_MODE: HVACMode.HEAT, ATTR_TEMPERATURE: 68}
    )
    assert send_command.await_args_list == [
        call(DeviceCommand.SET_THERMOSTAT_MODE, "heat"),
        call(DeviceCommand.SET_HEATING_SETPOINT, 68),
    ]


@pytest.mark.asyncio
async def test_thermostat_set_fan_mode_with_set_fan_mode() -> None:
    thermostat, send_command = _thermostat_with_modes(
        fan_modes="[on, auto, circulate]", commands=[DeviceCommand.SET_FAN_MODE]
    )
    for mode in ("on", "auto", "circulate"):
        await thermostat.async_set_fan_mode(mode)
    assert send_command.await_args_list == [
        call(DeviceCommand.SET_FAN_MODE, "on"),
        call(DeviceCommand.SET_FAN_MODE, "auto"),
        call(DeviceCommand.SET_FAN_MODE, "circulate"),
    ]


@pytest.mark.asyncio
async def test_thermostat_set_fan_mode_commands() -> None:
    thermostat, send_command = _thermostat_with_modes(fan_modes="[on, auto, circulate]")
    for mode in ("on", "auto", "circulate"):
        await thermostat.async_set_fan_mode(mode)
    assert send_command.await_args_list == [
        call(DeviceCommand.FAN_ON),
        call(DeviceCommand.FAN_AUTO),
        call(DeviceCommand.FAN_CIRCULATE),
    ]
