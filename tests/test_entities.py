from asyncio import Future
from typing import Awaitable

from custom_components.hubitat.device import Hub
from hubitatmaker import Device
from pytest_homeassistant_custom_component.async_mock import (
    Mock,
    NonCallableMock,
    call,
    patch,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


@patch("custom_components.hubitat.entities.get_hub")
@patch("custom_components.hubitat.entities.entity_registry")
async def test_entity_migration(get_hub: Mock, entity_registry: Mock) -> None:
    mock_device_1 = NonCallableMock(type="switch", attributes=["state"])
    mock_device_2 = NonCallableMock(type="fan", attributes=["state"])
    MockHub = Mock(spec=Hub)
    mock_hub = MockHub()
    mock_hub.configure_mock(devices={"id1": mock_device_1, "id2": mock_device_2})

    get_hub.return_value = mock_hub

    from homeassistant.helpers.entity_registry import EntityRegistry

    mock_reg = Mock(spec=EntityRegistry)

    def async_get_reg(_: HomeAssistant) -> Awaitable[EntityRegistry]:
        future: Future[EntityRegistry] = Future()
        future.set_result(mock_reg)
        return future

    mock_async_get_reg = Mock(side_effect=async_get_reg)
    entity_registry.configure_mock(async_get_registry=mock_async_get_reg)

    from custom_components.hubitat.switch import HubitatSwitch
    from custom_components.hubitat.entities import create_and_add_entities

    mock_hass = Mock(spec=["async_create_task"])
    MockConfigEntry = Mock(spec=ConfigEntry)
    mock_entry = MockConfigEntry()

    def _is_switch(device: Device) -> bool:
        return device.type == "switch"

    is_switch = Mock(side_effect=_is_switch)

    mock_async_add_entities = Mock()

    await create_and_add_entities(
        mock_hass,
        mock_entry,
        mock_async_add_entities,
        "switch",
        HubitatSwitch,
        is_switch,
    )


@patch("custom_components.hubitat.entities.get_hub")
@patch("custom_components.hubitat.entities.HubitatEventEmitter")
async def test_add_event_emitters(HubitatEventEmitter: Mock, get_hub: Mock) -> None:
    mock_device_1 = NonCallableMock(type="switch", attributes=["state"])
    mock_device_2 = NonCallableMock(type="button", attributes=["state"])
    MockHub = Mock(spec=Hub)
    mock_hub = MockHub()
    mock_hub.devices = {"id1": mock_device_1, "id2": mock_device_2}
    get_hub.return_value = mock_hub

    HubitatEventEmitter.return_value.update_device_registry = Mock(
        return_value="update_registry"
    )

    from custom_components.hubitat.entities import create_and_add_event_emitters

    mock_hass = Mock(spec=["async_create_task"])
    MockConfigEntry = Mock(spec=ConfigEntry)
    mock_entry = MockConfigEntry()

    def mock_is_emitter(device: Device) -> bool:
        return device.type == "button"

    is_emitter = Mock(side_effect=mock_is_emitter)

    await create_and_add_event_emitters(mock_hass, mock_entry, is_emitter)

    assert HubitatEventEmitter.call_count == 1, "expected 1 emitter to be created"
    assert mock_hass.async_create_task.call_count == 1, "expected 1 async creations"

    assert mock_hass.async_create_task.has_calls(
        [call("update_registry")]
    ), "1 update_device_registry task should have been created"

    assert (
        mock_hub.add_event_emitters.call_count == 1
    ), "event emitters should have been added to hub"
