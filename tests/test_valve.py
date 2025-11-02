# pyright: reportPrivateUsage=false

from unittest.mock import Mock

from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from custom_components.hubitat.hubitatmaker.types import Attribute
from custom_components.hubitat.valve import HubitatValve
from homeassistant.components.valve import ValveDeviceClass, ValveEntityFeature


def test_valve_init():
    """Test that a valve can be initialized."""
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
                    "currentValue": "closed",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    valve = HubitatValve(hub=hub, device=device)

    assert valve._attr_is_closed is True
    assert valve._attr_is_open is False
    assert valve.reports_position is False


def test_valve_open():
    """Test that a valve correctly reports open state."""
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

    valve = HubitatValve(hub=hub, device=device)

    assert valve._attr_is_open is True
    assert valve._attr_is_closed is False


def test_valve_water_device_class():
    """Test that a water valve has WATER device class."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Water Valve",
        label="Water Valve",
        attributes={
            DeviceAttribute.VALVE: Attribute(
                {
                    "name": DeviceAttribute.VALVE,
                    "currentValue": "closed",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    valve = HubitatValve(hub=hub, device=device)

    assert valve._attr_device_class == ValveDeviceClass.WATER


def test_valve_gas_device_class():
    """Test that a gas valve has GAS device class."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Gas Shutoff",
        label="Gas Shutoff",
        attributes={
            DeviceAttribute.VALVE: Attribute(
                {
                    "name": DeviceAttribute.VALVE,
                    "currentValue": "closed",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    valve = HubitatValve(hub=hub, device=device)

    assert valve._attr_device_class == ValveDeviceClass.GAS


def test_valve_supported_features():
    """Test that valve has correct supported features."""
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
                    "currentValue": "closed",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    valve = HubitatValve(hub=hub, device=device)

    assert valve._attr_supported_features == (
        ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
    )


def test_valve_device_attrs():
    """Test that device_attrs returns the correct attributes."""
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
                    "currentValue": "closed",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    valve = HubitatValve(hub=hub, device=device)

    assert valve.device_attrs == (DeviceAttribute.VALVE,)


def test_valve_case_variations():
    """Test that valve detects gas in various cases."""
    test_cases = [
        ("Gas Valve", ValveDeviceClass.GAS),
        ("gas valve", ValveDeviceClass.GAS),
        ("GAS SHUTOFF", ValveDeviceClass.GAS),
        ("Natural Gas Line", ValveDeviceClass.GAS),
        ("Water Main", ValveDeviceClass.WATER),
        ("Irrigation Valve", ValveDeviceClass.WATER),
    ]

    for label, expected_class in test_cases:
        hub = Mock()

        hub.configure_mock(token="test-token")
        device = Mock()
        device.configure_mock(
            id="test-id",
            name=label,
            label=label,
            attributes={
                DeviceAttribute.VALVE: Attribute(
                    {
                        "name": DeviceAttribute.VALVE,
                        "currentValue": "closed",
                        "dataType": "STRING",
                        "unit": None,
                    }
                )
            },
        )

        valve = HubitatValve(hub=hub, device=device)
        assert valve._attr_device_class == expected_class, f"Failed for label: {label}"
