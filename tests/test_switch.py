from asyncio import Future
from typing import Any, Awaitable, List

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity


@pytest.mark.asyncio
async def test_setup_entry(mocker) -> None:  # type: ignore
    def create_entities(*args: Any) -> Awaitable[List[Any]]:
        future: Future[List[Any]] = Future()
        future.set_result([])
        return future

    mock_create_entities = mocker.patch(
        "custom_components.hubitat.entities.create_and_add_entities"
    )
    mock_create_entities.side_effect = create_entities

    mock_create_emitters = mocker.patch(
        "custom_components.hubitat.entities.create_and_add_event_emitters"
    )
    mock_create_emitters.return_value = Future()
    mock_create_emitters.return_value.set_result(None)

    from custom_components.hubitat.switch import (
        async_setup_entry,
        HubitatSwitch,
        HubitatPowerMeterSwitch,
    )

    mock_hass = mocker.Mock(spec=["async_register"])
    mock_config_entry = mocker.Mock(spec=ConfigEntry)

    def add_entities(entities: List[Entity]) -> None:
        pass

    mock_add_entities = mocker.Mock(spec=add_entities)

    await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

    assert mock_create_entities.call_count == 3, "expected 3 calls to create entities"

    call1 = mocker.call(
        mock_hass, mock_config_entry, mock_add_entities, "switch", HubitatSwitch
    )
    call2 = mocker.call(
        mock_hass,
        mock_config_entry,
        mock_add_entities,
        "switch",
        HubitatPowerMeterSwitch,
    )
    call3 = mocker.call(
        mock_hass,
        mock_config_entry,
        mock_add_entities,
        "switch",
        HubitatPowerMeterSwitch,
    )
    assert mock_create_entities.has_calls([call1, call2, call3])

    assert mock_create_emitters.call_count == 1, "expected 1 call to create emitters"
