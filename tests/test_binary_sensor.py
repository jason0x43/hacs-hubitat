# pyright: reportAny=false, reportPrivateUsage=false

from unittest.mock import Mock

from custom_components.hubitat.binary_sensor import (
    HubitatAccelerationSensor,
    HubitatBinarySensor,
    HubitatContactSensor,
    HubitatCoSensor,
    HubitatHeatSensor,
    HubitatMoistureSensor,
    HubitatMotionSensor,
    HubitatNaturalGasSensor,
    HubitatNetworkStatusSensor,
    HubitatPresenceSensor,
    HubitatShockSensor,
    HubitatSmokeSensor,
    HubitatSoundSensor,
    HubitatTamperSensor,
    HubitatValveSensor,
)
from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from custom_components.hubitat.hubitatmaker.types import Attribute
from homeassistant.components.binary_sensor import BinarySensorDeviceClass


def test_binary_sensor_init():
    """Test that a binary sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Sensor",
        label="Test Sensor",
        attributes={
            DeviceAttribute.CONTACT: Attribute(
                {
                    "name": DeviceAttribute.CONTACT,
                    "currentValue": "open",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatBinarySensor(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.CONTACT,
        active_state="open",
        device_class=BinarySensorDeviceClass.DOOR,
    )

    assert sensor._attribute == DeviceAttribute.CONTACT
    assert sensor._active_state == "open"
    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.DOOR


def test_binary_sensor_inactive_state():
    """Test that a binary sensor correctly reports inactive state."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Sensor",
        label="Test Sensor",
        attributes={
            DeviceAttribute.CONTACT: Attribute(
                {
                    "name": DeviceAttribute.CONTACT,
                    "currentValue": "closed",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatBinarySensor(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.CONTACT,
        active_state="open",
        device_class=BinarySensorDeviceClass.DOOR,
    )

    assert sensor.is_on is False
    assert sensor.device_class == BinarySensorDeviceClass.DOOR


def test_binary_sensor_device_attrs():
    """Test that device_attrs returns the correct attributes."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Sensor",
        label="Test Sensor",
        attributes={
            DeviceAttribute.MOTION: Attribute(
                {
                    "name": DeviceAttribute.MOTION,
                    "currentValue": "active",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatBinarySensor(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.MOTION,
        active_state="active",
    )

    assert sensor.device_attrs == (DeviceAttribute.MOTION,)


def test_acceleration_sensor():
    """Test that an acceleration sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Accel",
        label="Test Accel",
        attributes={
            DeviceAttribute.ACCELERATION: Attribute(
                {
                    "name": DeviceAttribute.ACCELERATION,
                    "currentValue": "active",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatAccelerationSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.MOVING


def test_co_sensor():
    """Test that a CO sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test CO",
        label="Test CO",
        attributes={
            DeviceAttribute.CARBON_MONOXIDE: Attribute(
                {
                    "name": DeviceAttribute.CARBON_MONOXIDE,
                    "currentValue": "detected",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatCoSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.GAS


def test_contact_sensor_door():
    """Test that a contact sensor detects door from label."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Front Door",
        label="Front Door",
        attributes={
            DeviceAttribute.CONTACT: Attribute(
                {
                    "name": DeviceAttribute.CONTACT,
                    "currentValue": "open",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatContactSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.DOOR


def test_contact_sensor_window():
    """Test that a contact sensor detects window from label."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Kitchen Window",
        label="Kitchen Window",
        attributes={
            DeviceAttribute.CONTACT: Attribute(
                {
                    "name": DeviceAttribute.CONTACT,
                    "currentValue": "closed",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatContactSensor(hub=hub, device=device)

    assert sensor.is_on is False
    assert sensor.device_class == BinarySensorDeviceClass.WINDOW


def test_moisture_sensor():
    """Test that a moisture sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Moisture",
        label="Test Moisture",
        attributes={
            DeviceAttribute.WATER: Attribute(
                {
                    "name": DeviceAttribute.WATER,
                    "currentValue": "wet",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatMoistureSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.MOISTURE


def test_motion_sensor():
    """Test that a motion sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Motion",
        label="Test Motion",
        attributes={
            DeviceAttribute.MOTION: Attribute(
                {
                    "name": DeviceAttribute.MOTION,
                    "currentValue": "active",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatMotionSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.MOTION


def test_presence_sensor():
    """Test that a presence sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Presence",
        label="Test Presence",
        attributes={
            DeviceAttribute.PRESENCE: Attribute(
                {
                    "name": DeviceAttribute.PRESENCE,
                    "currentValue": "present",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatPresenceSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.PRESENCE


def test_smoke_sensor():
    """Test that a smoke sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Smoke",
        label="Test Smoke",
        attributes={
            DeviceAttribute.SMOKE: Attribute(
                {
                    "name": DeviceAttribute.SMOKE,
                    "currentValue": "detected",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatSmokeSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.SMOKE


def test_natural_gas_sensor():
    """Test that a natural gas sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Natural Gas",
        label="Test Natural Gas",
        attributes={
            DeviceAttribute.NATURAL_GAS: Attribute(
                {
                    "name": DeviceAttribute.NATURAL_GAS,
                    "currentValue": "detected",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatNaturalGasSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.GAS


def test_network_status_sensor():
    """Test that a network status sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Network",
        label="Test Network",
        attributes={
            DeviceAttribute.NETWORK_STATUS: Attribute(
                {
                    "name": DeviceAttribute.NETWORK_STATUS,
                    "currentValue": "online",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatNetworkStatusSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY


def test_sound_sensor():
    """Test that a sound sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Sound",
        label="Test Sound",
        attributes={
            DeviceAttribute.SOUND: Attribute(
                {
                    "name": DeviceAttribute.SOUND,
                    "currentValue": "detected",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatSoundSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.SOUND


def test_tamper_sensor():
    """Test that a tamper sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Tamper",
        label="Test Tamper",
        attributes={
            DeviceAttribute.TAMPER: Attribute(
                {
                    "name": DeviceAttribute.TAMPER,
                    "currentValue": "detected",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatTamperSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.TAMPER


def test_shock_sensor():
    """Test that a shock sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Shock",
        label="Test Shock",
        attributes={
            DeviceAttribute.SHOCK: Attribute(
                {
                    "name": DeviceAttribute.SHOCK,
                    "currentValue": "detected",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatShockSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.VIBRATION


def test_heat_sensor():
    """Test that a heat sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Heat",
        label="Test Heat",
        attributes={
            DeviceAttribute.HEAT_ALARM: Attribute(
                {
                    "name": DeviceAttribute.HEAT_ALARM,
                    "currentValue": "overheat",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatHeatSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.HEAT


def test_valve_sensor():
    """Test that a valve sensor can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Valve",
        label="Test Valve",
        attributes={
            DeviceAttribute.VALVE: Attribute(
                {
                    "name": DeviceAttribute.VALVE,
                    "currentValue": "open",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    sensor = HubitatValveSensor(hub=hub, device=device)

    assert sensor.is_on is True
    assert sensor.device_class == BinarySensorDeviceClass.OPENING
