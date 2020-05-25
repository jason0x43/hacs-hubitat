from typing import Any

from custom_components.hubitat.device import Hub
import pytest

from homeassistant.config_entries import ConfigEntry


@pytest.mark.asyncio
async def test_add_event_emitters(mocker) -> None:  # type: ignore
    MockHub = mocker.Mock(spec=Hub)
    mock_hub = MockHub()
    mock_hub.configure_mock(devices={"id1": "emitter", "id2": "fan"})

    mock_get_hub = mocker.patch("custom_components.hubitat.device.get_hub")
    mock_get_hub.return_value = mock_hub

    MockEventEmitter = mocker.patch(
        "custom_components.hubitat.device.HubitatEventEmitter"
    )
    MockEventEmitter.return_value.update_device_registry = mocker.Mock(
        return_value="update_registry"
    )

    from custom_components.hubitat.entities import create_and_add_event_emitters

    mock_hass = mocker.Mock(spec=["async_create_task"])
    MockConfigEntry = mocker.Mock(spec=ConfigEntry)
    mock_entry = MockConfigEntry()

    def mock_is_emitter(*args: str, **kwargs: Any) -> bool:
        return args[0] == "emitter"

    is_emitter = mocker.Mock(side_effect=mock_is_emitter)

    await create_and_add_event_emitters(mock_hass, mock_entry, is_emitter)

    assert MockEventEmitter.call_count == 1, "expected 1 emitter to be created"
    assert mock_hass.async_create_task.call_count == 1, "expected 1 async creations"

    call = mocker.call("update_registry")
    assert mock_hass.async_create_task.has_calls(
        [call]
    ), "1 update_device_registry task should have been created"

    assert (
        mock_hub.add_event_emitters.call_count == 1
    ), "event emitters should have been added to hub"
