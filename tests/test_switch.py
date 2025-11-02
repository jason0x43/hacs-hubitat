from typing import TypeVar
from unittest.mock import Mock, call, patch

import pytest

from custom_components.hubitat.device import HubitatEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity

E = TypeVar("E", bound=HubitatEntity)


@pytest.mark.asyncio
@patch("custom_components.hubitat.switch.create_and_add_entities")
@patch("custom_components.hubitat.switch.create_and_add_event_emitters")
async def test_setup_entry(
    create_emitters: Mock,
    create_entities: Mock,
) -> None:
    create_entities.return_value = []
    create_emitters.return_value = None

    from custom_components.hubitat.switch import (
        HubitatAlarm,
        HubitatPowerMeterSwitch,
        HubitatSwitch,
        async_setup_entry,
        is_alarm,
        is_simple_switch,
        is_smart_switch,
    )

    mock_hass = Mock(spec=["async_register"])
    mock_config_entry = Mock(spec=ConfigEntry)

    def add_entities(_: list[Entity]) -> None:
        pass

    mock_add_entities = Mock(spec=add_entities)

    await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

    assert create_entities.call_count == 3, "expected 3 calls to create entities"

    call1 = call(
        mock_hass,
        mock_config_entry,
        mock_add_entities,
        "switch",
        HubitatSwitch,
        is_simple_switch,
    )
    call2 = call(
        mock_hass,
        mock_config_entry,
        mock_add_entities,
        "switch",
        HubitatPowerMeterSwitch,
        is_smart_switch,
    )
    call3 = call(
        mock_hass,
        mock_config_entry,
        mock_add_entities,
        "switch",
        HubitatAlarm,
        is_alarm,
    )

    create_entities.assert_has_calls([call1, call2, call3])

    assert create_emitters.call_count == 1, "expected 1 call to create emitters"
