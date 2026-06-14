from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from custom_components.hubitat.cover import (
    HubitatCover,
    HubitatDoorControl,
    HubitatGarageDoorControl,
    HubitatWindowBlind,
    HubitatWindowControl,
    HubitatWindowShade,
    _is_cover_type,
    async_setup_entry,
    is_cover,
)
from custom_components.hubitat.hubitatmaker.const import (
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
)
from custom_components.hubitat.hubitatmaker.types import Attribute
from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntityFeature,
)


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
    assert cover.device_class == CoverDeviceClass.DOOR


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
    assert cover.device_class == CoverDeviceClass.GARAGE


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
    assert cover.device_class == CoverDeviceClass.SHADE


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
    assert cover.device_class == CoverDeviceClass.BLIND


def test_door_and_window_controls() -> None:
    hub = Mock(token="test-token")
    door = Mock(
        id="door",
        name="Door",
        label="Door",
        attributes={
            DeviceAttribute.DOOR: Attribute(
                {
                    "name": DeviceAttribute.DOOR,
                    "currentValue": "closed",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )
    window = Mock(
        id="window",
        name="Window",
        label="Window",
        attributes={
            DeviceAttribute.WINDOW_SHADE: Attribute(
                {
                    "name": DeviceAttribute.WINDOW_SHADE,
                    "currentValue": "open",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )

    assert (
        HubitatDoorControl(hub=hub, device=door).device_class == CoverDeviceClass.DOOR
    )
    assert (
        HubitatWindowControl(hub=hub, device=window).device_class
        == CoverDeviceClass.WINDOW
    )


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


@pytest.mark.asyncio
async def test_cover_commands() -> None:
    hub = Mock(token="test-token")
    device = Mock(
        id="test-id",
        name="Test Cover",
        label="Test Cover",
        attributes={},
    )
    cover = HubitatCover(
        hub=hub,
        device=device,
        attribute=DeviceAttribute.DOOR,
        features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
    )
    cover.send_command = AsyncMock()  # type: ignore[method-assign]

    await cover.async_close_cover()
    await cover.async_open_cover()
    await cover.async_set_cover_position(**{ATTR_POSITION: 42})

    cover.send_command.assert_has_awaits(
        [
            call(DeviceCommand.CLOSE),
            call(DeviceCommand.OPEN),
            call(DeviceCommand.SET_POSITION, 42),
        ]
    )


@pytest.mark.parametrize(
    ("capabilities", "expected_type"),
    [
        ({DeviceCapability.WINDOW_SHADE}, DeviceCapability.WINDOW_SHADE),
        ({DeviceCapability.WINDOW_BLIND}, DeviceCapability.WINDOW_BLIND),
        ({DeviceCapability.GARAGE_DOOR_CONTROL}, DeviceCapability.GARAGE_DOOR_CONTROL),
        ({DeviceCapability.DOOR_CONTROL}, DeviceCapability.DOOR_CONTROL),
        (set(), None),
    ],
)
def test_cover_detection(
    capabilities: set[DeviceCapability],
    expected_type: DeviceCapability | None,
) -> None:
    device = Mock(capabilities=capabilities)
    assert is_cover(device) is (expected_type is not None)

    for capability in (
        DeviceCapability.WINDOW_SHADE,
        DeviceCapability.WINDOW_BLIND,
        DeviceCapability.GARAGE_DOOR_CONTROL,
        DeviceCapability.DOOR_CONTROL,
    ):
        assert _is_cover_type(device, capability) is (capability == expected_type)


@pytest.mark.asyncio
async def test_cover_setup_entry() -> None:
    with patch("custom_components.hubitat.cover.create_and_add_entities") as create:
        await async_setup_entry(Mock(), Mock(), Mock())

    assert create.call_count == 4
    matchers = [item.args[-1] for item in create.call_args_list]
    devices = [
        Mock(capabilities={DeviceCapability.GARAGE_DOOR_CONTROL}),
        Mock(capabilities={DeviceCapability.WINDOW_BLIND}),
        Mock(capabilities={DeviceCapability.WINDOW_SHADE}),
    ]
    assert sum(matcher(device) for matcher in matchers for device in devices) == 3
