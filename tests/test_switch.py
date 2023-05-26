from typing import List
from unittest.mock import Mock, call, patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity


@pytest.mark.asyncio
@patch("custom_components.hubitat.switch.create_and_add_entities")
@patch("custom_components.hubitat.switch.create_and_add_event_emitters")
async def test_setup_entry(create_emitters, create_entities) -> None:
    create_entities.return_value = []
    create_emitters.return_value = None

    from custom_components.hubitat.switch import (
        HubitatPowerMeterSwitch,
        HubitatSwitch,
        async_setup_entry,
    )

    mock_hass = Mock(spec=["async_register"])
    mock_config_entry = Mock(spec=ConfigEntry)

    def add_entities(_: List[Entity]) -> None:
        pass

    mock_add_entities = Mock(spec=add_entities)

    await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

    assert create_entities.call_count == 3, "expected 3 calls to create entities"

    call1 = call(
        mock_hass, mock_config_entry, mock_add_entities, "switch", HubitatSwitch
    )
    call2 = call(
        mock_hass,
        mock_config_entry,
        mock_add_entities,
        "switch",
        HubitatPowerMeterSwitch,
    )
    call3 = call(
        mock_hass,
        mock_config_entry,
        mock_add_entities,
        "switch",
        HubitatPowerMeterSwitch,
    )
    assert create_entities.has_calls([call1, call2, call3])

    assert create_emitters.call_count == 1, "expected 1 call to create emitters"
