from unittest.mock import Mock

from custom_components.hubitat.fan import HubitatFan
from custom_components.hubitat.hubitatmaker.const import (
    DeviceAttribute,
    DeviceCapability,
)
from custom_components.hubitat.hubitatmaker.types import Attribute


def test_fan_init():
    """Test that a fan can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Fan",
        label="Test Fan",
        capabilities={DeviceCapability.FAN_CONTROL, DeviceCapability.SWITCH},
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.SPEED: Attribute(
                {
                    "name": DeviceAttribute.SPEED,
                    "currentValue": "medium",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    fan = HubitatFan(hub=hub, device=device)

    assert fan.is_on is True


def test_fan_off():
    """Test that a fan correctly reports off state."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Fan",
        label="Test Fan",
        capabilities={DeviceCapability.FAN_CONTROL, DeviceCapability.SWITCH},
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "off",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.SPEED: Attribute(
                {
                    "name": DeviceAttribute.SPEED,
                    "currentValue": "off",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    fan = HubitatFan(hub=hub, device=device)

    assert fan.is_on is False


def test_fan_percentage():
    """Test that fan reports percentage correctly."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Fan",
        label="Test Fan",
        capabilities={DeviceCapability.FAN_CONTROL},
        attributes={
            DeviceAttribute.SPEED: Attribute(
                {
                    "name": DeviceAttribute.SPEED,
                    "currentValue": "medium",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.SUPPORTED_FAN_SPEEDS: Attribute(
                {
                    "name": DeviceAttribute.SUPPORTED_FAN_SPEEDS,
                    "currentValue": '["low","medium-low","medium","medium-high","high"]',  # noqa: E501
                    "dataType": "JSON_OBJECT",
                    "unit": None,
                }
            ),
        },
    )

    fan = HubitatFan(hub=hub, device=device)

    # medium is 3rd of 5 speeds, so should be around 60%
    assert fan.percentage is not None
    assert 40 < fan.percentage < 80


def test_fan_speed_count():
    """Test that fan reports correct speed count."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Fan",
        label="Test Fan",
        capabilities={DeviceCapability.FAN_CONTROL},
        attributes={
            DeviceAttribute.SPEED: Attribute(
                {
                    "name": DeviceAttribute.SPEED,
                    "currentValue": "low",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.SUPPORTED_FAN_SPEEDS: Attribute(
                {
                    "name": DeviceAttribute.SUPPORTED_FAN_SPEEDS,
                    "currentValue": '["low","medium","high"]',
                    "dataType": "JSON_OBJECT",
                    "unit": None,
                }
            ),
        },
    )

    fan = HubitatFan(hub=hub, device=device)

    assert fan.speed_count == 3


def test_fan_speeds_property():
    """Test that fan.speeds excludes on/off/auto."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Fan",
        label="Test Fan",
        capabilities={DeviceCapability.FAN_CONTROL},
        attributes={
            DeviceAttribute.SPEED: Attribute(
                {
                    "name": DeviceAttribute.SPEED,
                    "currentValue": "low",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.SUPPORTED_FAN_SPEEDS: Attribute(
                {
                    "name": DeviceAttribute.SUPPORTED_FAN_SPEEDS,
                    "currentValue": '["on","low","medium","high","auto","off"]',
                    "dataType": "JSON_OBJECT",
                    "unit": None,
                }
            ),
        },
    )

    fan = HubitatFan(hub=hub, device=device)

    speeds = fan.speeds
    assert "on" not in speeds
    assert "off" not in speeds
    assert "auto" not in speeds
    assert "low" in speeds
    assert "medium" in speeds
    assert "high" in speeds


def test_fan_preset_mode_auto():
    """Test that fan reports auto preset mode."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Fan",
        label="Test Fan",
        capabilities={DeviceCapability.FAN_CONTROL},
        attributes={
            DeviceAttribute.SPEED: Attribute(
                {
                    "name": DeviceAttribute.SPEED,
                    "currentValue": "auto",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.SUPPORTED_FAN_SPEEDS: Attribute(
                {
                    "name": DeviceAttribute.SUPPORTED_FAN_SPEEDS,
                    "currentValue": '["low","medium","high","auto"]',
                    "dataType": "JSON_OBJECT",
                    "unit": None,
                }
            ),
        },
    )

    fan = HubitatFan(hub=hub, device=device)

    assert fan.preset_mode == "auto"
    assert fan.preset_modes == ["auto"]


def test_fan_no_preset_mode():
    """Test that fan without auto has no preset mode."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Fan",
        label="Test Fan",
        capabilities={DeviceCapability.FAN_CONTROL},
        attributes={
            DeviceAttribute.SPEED: Attribute(
                {
                    "name": DeviceAttribute.SPEED,
                    "currentValue": "low",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.SUPPORTED_FAN_SPEEDS: Attribute(
                {
                    "name": DeviceAttribute.SUPPORTED_FAN_SPEEDS,
                    "currentValue": '["low","medium","high"]',
                    "dataType": "JSON_OBJECT",
                    "unit": None,
                }
            ),
        },
    )

    fan = HubitatFan(hub=hub, device=device)

    assert fan.preset_mode is None
    assert fan.preset_modes is None


def test_fan_percentage_100_for_on():
    """Test that fan reports 100% for 'on' speed."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Fan",
        label="Test Fan",
        capabilities={DeviceCapability.FAN_CONTROL},
        attributes={
            DeviceAttribute.SPEED: Attribute(
                {
                    "name": DeviceAttribute.SPEED,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    fan = HubitatFan(hub=hub, device=device)

    assert fan.percentage == 100


def test_fan_percentage_none_for_off():
    """Test that fan reports None percentage for 'off' speed."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Fan",
        label="Test Fan",
        capabilities={DeviceCapability.FAN_CONTROL},
        attributes={
            DeviceAttribute.SPEED: Attribute(
                {
                    "name": DeviceAttribute.SPEED,
                    "currentValue": "off",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    fan = HubitatFan(hub=hub, device=device)

    assert fan.percentage is None


def test_fan_device_attrs():
    """Test that device_attrs returns the correct attributes."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        capabilities={DeviceCapability.FAN_CONTROL},
        attributes={
            DeviceAttribute.SPEED: Attribute(
                {
                    "name": DeviceAttribute.SPEED,
                    "currentValue": "low",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    fan = HubitatFan(hub=hub, device=device)

    attrs = fan.device_attrs
    assert attrs is not None
    assert DeviceAttribute.SWITCH in attrs
    assert DeviceAttribute.SPEED in attrs
