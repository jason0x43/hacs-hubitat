from unittest.mock import Mock

from custom_components.hubitat.cover import (
    HubitatCover,
    HubitatGarageDoorControl,
    HubitatWindowBlind,
    HubitatWindowShade,
)
from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from custom_components.hubitat.hubitatmaker.types import Attribute
from homeassistant.components.cover import CoverDeviceClass, CoverEntityFeature


def test_cover_init():
    """Test that a cover can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Cover",
        label="Test Cover",
        attributes={
            DeviceAttribute.DOOR: Attribute(
                {
                    "name": DeviceAttribute.DOOR,
                    "currentValue": "closed",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.POSITION: Attribute(
                {
                    "name": DeviceAttribute.POSITION,
                    "currentValue": "0",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
        },
    )

    cover = HubitatCover(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.DOOR,
        features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
        device_class=CoverDeviceClass.DOOR,
    )

    assert cover.is_closed is True
    assert cover.current_cover_position == 0


def test_cover_open():
    """Test that a cover correctly reports open state."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Cover",
        label="Test Cover",
        attributes={
            DeviceAttribute.DOOR: Attribute(
                {
                    "name": DeviceAttribute.DOOR,
                    "currentValue": "open",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.POSITION: Attribute(
                {
                    "name": DeviceAttribute.POSITION,
                    "currentValue": "100",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
        },
    )

    cover = HubitatCover(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.DOOR,
        features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
    )

    assert cover.is_closed is False
    assert cover.current_cover_position == 100


def test_cover_partial_position():
    """Test that a cover reports partial position correctly."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Cover",
        label="Test Cover",
        attributes={
            DeviceAttribute.WINDOW_SHADE: Attribute(
                {
                    "name": DeviceAttribute.WINDOW_SHADE,
                    "currentValue": "open",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.POSITION: Attribute(
                {
                    "name": DeviceAttribute.POSITION,
                    "currentValue": "50",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
        },
    )

    cover = HubitatCover(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.WINDOW_SHADE,
        features=CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION,
    )

    assert cover.current_cover_position == 50


def test_cover_level_fallback():
    """Test that cover uses level attribute if position is not available."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Cover",
        label="Test Cover",
        attributes={
            DeviceAttribute.WINDOW_SHADE: Attribute(
                {
                    "name": DeviceAttribute.WINDOW_SHADE,
                    "currentValue": "open",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.LEVEL: Attribute(
                {
                    "name": DeviceAttribute.LEVEL,
                    "currentValue": "75",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
        },
    )

    cover = HubitatCover(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.WINDOW_SHADE,
        features=CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION,
    )

    assert cover.current_cover_position == 75


def test_cover_opening_state():
    """Test that cover reports opening state."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Cover",
        label="Test Cover",
        attributes={
            DeviceAttribute.DOOR: Attribute(
                {
                    "name": DeviceAttribute.DOOR,
                    "currentValue": "opening",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    cover = HubitatCover(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.DOOR,
        features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
    )

    assert cover.is_opening is True
    assert cover.is_closing is False


def test_cover_closing_state():
    """Test that cover reports closing state."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Cover",
        label="Test Cover",
        attributes={
            DeviceAttribute.DOOR: Attribute(
                {
                    "name": DeviceAttribute.DOOR,
                    "currentValue": "closing",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    cover = HubitatCover(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.DOOR,
        features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
    )

    assert cover.is_closing is True
    assert cover.is_opening is False


def test_garage_door_control():
    """Test that a garage door control can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Garage Door",
        label="Garage Door",
        attributes={
            DeviceAttribute.DOOR: Attribute(
                {
                    "name": DeviceAttribute.DOOR,
                    "currentValue": "closed",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    cover = HubitatGarageDoorControl(hub=hub, device=device)

    assert cover.supported_features == (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
    )
    assert cover.is_closed is True


def test_window_shade():
    """Test that a window shade can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Window Shade",
        label="Window Shade",
        attributes={
            DeviceAttribute.WINDOW_SHADE: Attribute(
                {
                    "name": DeviceAttribute.WINDOW_SHADE,
                    "currentValue": "open",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.POSITION: Attribute(
                {
                    "name": DeviceAttribute.POSITION,
                    "currentValue": "100",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ),
        },
    )

    cover = HubitatWindowShade(hub=hub, device=device)

    assert cover.supported_features == (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
    )
    assert cover.is_closed is False


def test_window_blind():
    """Test that a window blind can be initialized."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Window Blind",
        label="Window Blind",
        attributes={
            DeviceAttribute.WINDOW_BLIND: Attribute(
                {
                    "name": DeviceAttribute.WINDOW_BLIND,
                    "currentValue": "closed",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    cover = HubitatWindowBlind(hub=hub, device=device)

    assert cover.supported_features == (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
    )
    assert cover.is_closed is True


def test_cover_device_attrs():
    """Test that device_attrs returns the correct attributes."""
    hub = Mock()

    hub.configure_mock(token="test-token")
    device = Mock()
    device.configure_mock(
        id="test-id",
        attributes={
            DeviceAttribute.DOOR: Attribute(
                {
                    "name": DeviceAttribute.DOOR,
                    "currentValue": "closed",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    cover = HubitatCover(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.DOOR,
        features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
    )

    attrs = cover.device_attrs
    assert attrs is not None
    assert DeviceAttribute.DOOR in attrs
    assert DeviceAttribute.LEVEL in attrs
    assert DeviceAttribute.POSITION in attrs
