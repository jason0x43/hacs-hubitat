from unittest.mock import Mock

from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from custom_components.hubitat.hubitatmaker.types import Attribute
from custom_components.hubitat.sensor import (
    HubitatBatterySensor,
    HubitatCurrentSensor,
    HubitatDewPointSensor,
    HubitatEnergySensor,
    HubitatHumiditySensor,
    HubitatIlluminanceSensor,
    HubitatPowerSensor,
    HubitatPressureSensor,
    HubitatSensor,
    HubitatTemperatureSensor,
    HubitatVoltageSensor,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
)


def test_sensor_init():
    """Test that a generic sensor can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Sensor",
        label="Test Sensor",
        attributes={
            DeviceAttribute.TEMPERATURE: Attribute(
                {
                    "name": DeviceAttribute.TEMPERATURE,
                    "currentValue": "72.5",
                    "dataType": "NUMBER",
                    "unit": "",
                }
            )
        },
    )

    sensor = HubitatSensor(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.TEMPERATURE,
    )

    assert sensor.native_value == "72.5"
    assert sensor.device_attrs == (DeviceAttribute.TEMPERATURE,)


def test_battery_sensor():
    """Test that a battery sensor can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Battery",
        label="Test Battery",
        attributes={
            DeviceAttribute.BATTERY: Attribute(
                {
                    "name": DeviceAttribute.BATTERY,
                    "currentValue": "85",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatBatterySensor(hub=hub, device=device)

    assert sensor.native_value == 85.0
    assert sensor.device_class == SensorDeviceClass.BATTERY
    assert sensor.native_unit_of_measurement == PERCENTAGE
    assert sensor.state_class == SensorStateClass.MEASUREMENT


def test_battery_sensor_string_value():
    """Test that battery sensor handles string values."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Battery",
        label="Test Battery",
        attributes={
            DeviceAttribute.BATTERY: Attribute(
                {
                    "name": DeviceAttribute.BATTERY,
                    "currentValue": "Battery 90%",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatBatterySensor(hub=hub, device=device)

    # Should extract "90" from "Battery 90%"
    assert sensor.native_value == 90.0


def test_temperature_sensor():
    """Test that a temperature sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Temp",
        label="Test Temp",
        attributes={
            DeviceAttribute.TEMPERATURE: Attribute(
                {
                    "name": DeviceAttribute.TEMPERATURE,
                    "currentValue": "72.5",
                    "dataType": "NUMBER",
                    "unit": "°F",
                }
            )
        },
    )

    sensor = HubitatTemperatureSensor(hub=hub, device=device)

    assert sensor.native_value == "72.5"
    assert sensor.device_class == SensorDeviceClass.TEMPERATURE
    assert sensor.state_class == SensorStateClass.MEASUREMENT
    assert sensor.native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT


def test_temperature_sensor_celsius():
    """Test that temperature sensor handles Celsius."""
    hub = Mock()
    hub.configure_mock(token="test-token", temperature_unit=UnitOfTemperature.CELSIUS)

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Temp",
        label="Test Temp",
        attributes={
            DeviceAttribute.TEMPERATURE: Attribute(
                {
                    "name": DeviceAttribute.TEMPERATURE,
                    "currentValue": "22.5",
                    "dataType": "NUMBER",
                    "unit": "°C",
                }
            )
        },
    )

    sensor = HubitatTemperatureSensor(hub=hub, device=device)

    assert sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS


def test_humidity_sensor():
    """Test that a humidity sensor can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Humidity",
        label="Test Humidity",
        attributes={
            DeviceAttribute.HUMIDITY: Attribute(
                {
                    "name": DeviceAttribute.HUMIDITY,
                    "currentValue": "45",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatHumiditySensor(hub=hub, device=device)

    assert sensor.native_value == "45"
    assert sensor.device_class == SensorDeviceClass.HUMIDITY
    assert sensor.native_unit_of_measurement == PERCENTAGE


def test_illuminance_sensor():
    """Test that an illuminance sensor can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Lux",
        label="Test Lux",
        attributes={
            DeviceAttribute.ILLUMINANCE: Attribute(
                {
                    "name": DeviceAttribute.ILLUMINANCE,
                    "currentValue": "150",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatIlluminanceSensor(hub=hub, device=device)

    assert sensor.native_value == "150"
    assert sensor.device_class == SensorDeviceClass.ILLUMINANCE


def test_power_sensor():
    """Test that a power sensor can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Power",
        label="Test Power",
        attributes={
            DeviceAttribute.POWER: Attribute(
                {
                    "name": DeviceAttribute.POWER,
                    "currentValue": "125.5",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatPowerSensor(hub=hub, device=device)

    assert sensor.native_value == "125.5"
    assert sensor.device_class == SensorDeviceClass.POWER
    assert sensor.native_unit_of_measurement == UnitOfPower.WATT
    assert sensor.state_class == SensorStateClass.MEASUREMENT


def test_energy_sensor():
    """Test that an energy sensor can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Energy",
        label="Test Energy",
        attributes={
            DeviceAttribute.ENERGY: Attribute(
                {
                    "name": DeviceAttribute.ENERGY,
                    "currentValue": "25.5",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatEnergySensor(hub=hub, device=device)

    assert sensor.native_value == "25.5"
    assert sensor.device_class == SensorDeviceClass.ENERGY
    assert sensor.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR
    assert sensor.state_class == SensorStateClass.TOTAL


def test_voltage_sensor():
    """Test that a voltage sensor can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Voltage",
        label="Test Voltage",
        attributes={
            DeviceAttribute.VOLTAGE: Attribute(
                {
                    "name": DeviceAttribute.VOLTAGE,
                    "currentValue": "120.5",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatVoltageSensor(hub=hub, device=device)

    assert sensor.native_value == "120.5"
    assert sensor.device_class == SensorDeviceClass.VOLTAGE
    assert sensor.native_unit_of_measurement == UnitOfElectricPotential.VOLT


def test_current_sensor():
    """Test that a current sensor can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Current",
        label="Test Current",
        attributes={
            DeviceAttribute.AMPERAGE: Attribute(
                {
                    "name": DeviceAttribute.AMPERAGE,
                    "currentValue": "5.5",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatCurrentSensor(hub=hub, device=device)

    assert sensor.native_value == "5.5"
    assert sensor.device_class == SensorDeviceClass.CURRENT
    assert sensor.native_unit_of_measurement == UnitOfElectricCurrent.AMPERE


def test_pressure_sensor():
    """Test that a pressure sensor can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Pressure",
        label="Test Pressure",
        attributes={
            DeviceAttribute.PRESSURE: Attribute(
                {
                    "name": DeviceAttribute.PRESSURE,
                    "currentValue": "1013",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatPressureSensor(hub=hub, device=device)

    assert sensor.native_value == "1013"
    assert sensor.device_class == SensorDeviceClass.PRESSURE
    # Default is mbar
    assert sensor.native_unit_of_measurement == UnitOfPressure.MBAR


def test_pressure_sensor_with_unit():
    """Test that pressure sensor uses Hubitat unit if available."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Pressure",
        label="Test Pressure",
        attributes={
            DeviceAttribute.PRESSURE: Attribute(
                {
                    "name": DeviceAttribute.PRESSURE,
                    "currentValue": "29.92",
                    "dataType": "NUMBER",
                    "unit": "inHg",
                }
            )
        },
    )

    sensor = HubitatPressureSensor(hub=hub, device=device)

    assert sensor.native_unit_of_measurement == UnitOfPressure.INHG


def test_dewpoint_sensor():
    """Test that a dewpoint sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(
        token="test-token", temperature_unit=UnitOfTemperature.FAHRENHEIT
    )

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Dewpoint",
        label="Test Dewpoint",
        attributes={
            DeviceAttribute.DEW_POINT: Attribute(
                {
                    "name": DeviceAttribute.DEW_POINT,
                    "currentValue": "55",
                    "dataType": "NUMBER",
                    "unit": "°F",
                }
            )
        },
    )

    sensor = HubitatDewPointSensor(hub=hub, device=device)

    assert sensor.native_value == "55"
    assert sensor.device_class == SensorDeviceClass.TEMPERATURE
    assert sensor.native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT


def test_sensor_custom_name():
    """Test that sensor can have a custom name."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Device",
        label="Test Device",
        attributes={
            DeviceAttribute.TEMPERATURE: Attribute(
                {
                    "name": DeviceAttribute.TEMPERATURE,
                    "currentValue": "72",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatSensor(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.TEMPERATURE,
        attribute_name="Custom Temp",
    )

    name = sensor.name
    assert name is not None and isinstance(name, str)
    assert "Custom Temp" in name


def test_sensor_enabled_default():
    """Test that sensor respects enabled_default parameter."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Device",
        label="Test Device",
        attributes={
            DeviceAttribute.TEMPERATURE: Attribute(
                {
                    "name": DeviceAttribute.TEMPERATURE,
                    "currentValue": "72",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatSensor(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.TEMPERATURE,
        enabled_default=False,
    )

    assert sensor.entity_registry_enabled_default is False
