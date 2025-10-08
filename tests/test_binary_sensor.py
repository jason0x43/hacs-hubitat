# pyright: reportAny=false, reportPrivateUsage=false

from unittest.mock import Mock

from custom_components.hubitat.binary_sensor import (
    HubitatAccelerationSensor,
    HubitatBinarySensor,
    HubitatContactSensor,
    HubitatCoSensor,
    HubitatMoistureSensor,
    HubitatMotionSensor,
    HubitatPresenceSensor,
    HubitatSmokeSensor,
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
