from unittest.mock import Mock, patch

import pytest

from custom_components.hubitat.event import HubitatButtonEventEntity
from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from custom_components.hubitat.hubitatmaker.types import Attribute, Event
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


def test_button_event_entity_handles_matching_events():
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
            )
        },
    )
    entity = HubitatButtonEventEntity(button_id="1", hub=hub, device=device)
    entity._attr_entity_registry_enabled_default = True

    with (
        patch.object(entity, "_trigger_event") as trigger_event,
        patch.object(entity, "async_write_ha_state") as write_state,
    ):
        entity.handle_event(
            Event({"deviceId": "test-id", "name": "pushed", "value": "1"})
        )
        trigger_event.assert_called_once_with("pushed")
        write_state.assert_called_once()

        trigger_event.reset_mock()
        entity.handle_event(
            Event({"deviceId": "test-id", "name": "unknown", "value": "1"})
        )
        entity.handle_event(
            Event({"deviceId": "test-id", "name": "pushed", "value": "2"})
        )
        trigger_event.assert_not_called()


@pytest.mark.asyncio
async def test_button_event_setup_entry():
    button = Mock()
    button.configure_mock(
        id="button",
        name="Button",
        label="Button",
        attributes={
            DeviceAttribute.NUM_BUTTONS: Attribute(
                {
                    "name": DeviceAttribute.NUM_BUTTONS,
                    "currentValue": "2",
                    "dataType": "NUMBER",
                    "unit": None,
                }
            )
        },
    )
    no_buttons = Mock(attributes={})
    hub = Mock(devices={"button": button, "other": no_buttons}, add_entities=Mock())
    add_entities = Mock()

    with patch("custom_components.hubitat.event.get_hub", return_value=hub):
        from custom_components.hubitat.event import async_setup_entry

        await async_setup_entry(Mock(), Mock(entry_id="entry"), add_entities)

    entities = add_entities.call_args.args[0]
    assert [entity._button_id for entity in entities] == ["1", "2"]
    hub.add_entities.assert_called_once_with(entities)
