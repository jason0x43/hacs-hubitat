from unittest.mock import Mock

from custom_components.hubitat.event import HubitatButtonEventEntity
from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from custom_components.hubitat.hubitatmaker.types import Attribute
from homeassistant.components.event import EventDeviceClass


def test_button_event_entity_init():
    """Test that a button event entity can be initialized."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Button",
        label="Test Button",
        attributes={
            DeviceAttribute.PUSHED: Attribute(
                {
                    "name": DeviceAttribute.PUSHED,
                    "currentValue": "1",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.HELD: Attribute(
                {
                    "name": DeviceAttribute.HELD,
                    "currentValue": "1",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    entity = HubitatButtonEventEntity(button_id="1", hub=hub, device=device)

    assert entity._button_id == "1"
    assert entity.device_class == EventDeviceClass.BUTTON


def test_button_event_entity_device_class():
    """Test that button event entity has correct device class."""
    hub = Mock()
    hub.configure_mock(token="test-token")

    device = Mock()
    device.configure_mock(
        id="test-id",
        name="Test Button",
        label="Test Button",
        attributes={
            DeviceAttribute.PUSHED: Attribute(
                {
                    "name": DeviceAttribute.PUSHED,
                    "currentValue": "2",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
        },
    )

    entity = HubitatButtonEventEntity(button_id="2", hub=hub, device=device)

    assert entity.device_class == EventDeviceClass.BUTTON
