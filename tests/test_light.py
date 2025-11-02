from unittest.mock import Mock

from custom_components.hubitat.hubitatmaker.const import (
    DeviceAttribute,
    DeviceCapability,
)
from custom_components.hubitat.hubitatmaker.types import Attribute
from custom_components.hubitat.light import HubitatLight
from homeassistant.components.light.const import ColorMode


def test_light_init():
    """Test that a light can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Light",
        label="Test Light",
        capabilities={DeviceCapability.SWITCH, DeviceCapability.SWITCH_LEVEL},
        commands=["on", "off", "setLevel"],
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.LEVEL: Attribute(
                {
                    "name": DeviceAttribute.LEVEL,
                    "currentValue": "50",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
        },
    )

    light = HubitatLight(hub=hub, device=device)

    assert light.is_on is True
    assert light.brightness is not None


def test_light_off():
    """Test that a light correctly reports off state."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Light",
        label="Test Light",
        capabilities={DeviceCapability.SWITCH},
        commands=["on", "off"],
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "off",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    light = HubitatLight(hub=hub, device=device)

    assert light.is_on is False


def test_light_brightness():
    """Test that light reports brightness correctly."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Light",
        label="Test Light",
        capabilities={DeviceCapability.SWITCH, DeviceCapability.SWITCH_LEVEL},
        commands=["on", "off", "setLevel"],
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.LEVEL: Attribute(
                {
                    "name": DeviceAttribute.LEVEL,
                    "currentValue": "100",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
        },
    )

    light = HubitatLight(hub=hub, device=device)

    # 100% should be 255
    assert light.brightness == 255


def test_light_brightness_conversion():
    """Test that light converts brightness correctly (0-100 to 0-255)."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Light",
        label="Test Light",
        capabilities={DeviceCapability.SWITCH, DeviceCapability.SWITCH_LEVEL},
        commands=["on", "off", "setLevel"],
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.LEVEL: Attribute(
                {
                    "name": DeviceAttribute.LEVEL,
                    "currentValue": "50",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
        },
    )

    light = HubitatLight(hub=hub, device=device)

    # 50% should be ~128
    assert light.brightness == round(255 * 50 / 100)


def test_light_color_mode_onoff():
    """Test that simple switch reports ONOFF color mode."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Light",
        label="Test Light",
        capabilities={DeviceCapability.SWITCH},
        commands=["on", "off"],
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    light = HubitatLight(hub=hub, device=device)

    modes = light.supported_color_modes
    assert modes is not None
    assert ColorMode.ONOFF in modes
    assert light.color_mode == ColorMode.ONOFF


def test_light_color_mode_brightness():
    """Test that dimmable light reports BRIGHTNESS color mode."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Light",
        label="Test Light",
        capabilities={DeviceCapability.SWITCH, DeviceCapability.SWITCH_LEVEL},
        commands=["on", "off", "setLevel"],
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.LEVEL: Attribute(
                {
                    "name": DeviceAttribute.LEVEL,
                    "currentValue": "50",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
        },
    )

    light = HubitatLight(hub=hub, device=device)

    modes = light.supported_color_modes
    assert modes is not None
    assert ColorMode.BRIGHTNESS in modes
    assert light.color_mode == ColorMode.BRIGHTNESS


def test_light_color_mode_hs():
    """Test that RGB light reports HS color mode."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Light",
        label="Test Light",
        capabilities={
            DeviceCapability.SWITCH,
            DeviceCapability.SWITCH_LEVEL,
            DeviceCapability.COLOR_CONTROL,
        },
        commands=["on", "off", "setLevel", "setColor"],
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.LEVEL: Attribute(
                {
                    "name": DeviceAttribute.LEVEL,
                    "currentValue": "50",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
            DeviceAttribute.HUE: Attribute(
                {
                    "name": DeviceAttribute.HUE,
                    "currentValue": "50",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
            DeviceAttribute.SATURATION: Attribute(
                {
                    "name": DeviceAttribute.SATURATION,
                    "currentValue": "100",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
            DeviceAttribute.COLOR_MODE: Attribute(
                {
                    "name": DeviceAttribute.COLOR_MODE,
                    "currentValue": "RGB",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    light = HubitatLight(hub=hub, device=device)

    modes = light.supported_color_modes
    assert modes is not None
    assert ColorMode.HS in modes
    assert light.color_mode == ColorMode.HS


def test_light_hs_color():
    """Test that RGB light reports HS color correctly."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Light",
        label="Test Light",
        capabilities={
            DeviceCapability.SWITCH,
            DeviceCapability.SWITCH_LEVEL,
            DeviceCapability.COLOR_CONTROL,
        },
        commands=["on", "off", "setLevel", "setColor"],
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.HUE: Attribute(
                {
                    "name": DeviceAttribute.HUE,
                    "currentValue": "50",  # 50% of 100 = 180 degrees
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
            DeviceAttribute.SATURATION: Attribute(
                {
                    "name": DeviceAttribute.SATURATION,
                    "currentValue": "75",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
            DeviceAttribute.COLOR_MODE: Attribute(
                {
                    "name": DeviceAttribute.COLOR_MODE,
                    "currentValue": "RGB",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    light = HubitatLight(hub=hub, device=device)

    assert light.hs_color is not None
    hue, sat = light.hs_color
    assert hue == 180.0  # 50% of 360 degrees
    assert sat == 75.0


def test_light_color_temp():
    """Test that CT light reports color temp correctly."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Light",
        label="Test Light",
        capabilities={
            DeviceCapability.SWITCH,
            DeviceCapability.SWITCH_LEVEL,
            DeviceCapability.COLOR_TEMP,
        },
        commands=["on", "off", "setLevel", "setColorTemperature"],
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.COLOR_TEMP: Attribute(
                {
                    "name": DeviceAttribute.COLOR_TEMP,
                    "currentValue": "3000",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
            DeviceAttribute.COLOR_MODE: Attribute(
                {
                    "name": DeviceAttribute.COLOR_MODE,
                    "currentValue": "CT",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    light = HubitatLight(hub=hub, device=device)

    modes = light.supported_color_modes
    assert modes is not None
    assert ColorMode.COLOR_TEMP in modes
    assert light.color_mode == ColorMode.COLOR_TEMP
    assert light.color_temp_kelvin == 3000


def test_light_color_name():
    """Test that light reports color name."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Light",
        label="Test Light",
        capabilities={DeviceCapability.SWITCH, DeviceCapability.COLOR_CONTROL},
        commands=["on", "off", "setColor"],
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.COLOR_NAME: Attribute(
                {
                    "name": DeviceAttribute.COLOR_NAME,
                    "currentValue": "Red",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    light = HubitatLight(hub=hub, device=device)

    assert light.color_name == "Red"


def test_light_device_attrs():
    """Test that device_attrs returns the correct attributes."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        capabilities={DeviceCapability.SWITCH},
        commands=["on", "off"],
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    light = HubitatLight(hub=hub, device=device)

    attrs = light.device_attrs
    assert attrs is not None
    assert DeviceAttribute.SWITCH in attrs
    assert DeviceAttribute.LEVEL in attrs
    assert DeviceAttribute.COLOR_MODE in attrs
