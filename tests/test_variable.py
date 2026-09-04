"""Tests for Hubitat Hub Variable entities."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.hubitat.datetime import HubitatVariableDateTime
from custom_components.hubitat.hubitatmaker import HubVariable
from custom_components.hubitat.number import HubitatVariableNumber
from custom_components.hubitat.switch import HubitatVariableSwitch
from custom_components.hubitat.text import HubitatVariableText


def make_hub() -> Mock:
    hub = Mock()
    hub.id = "hub-id"
    hub.add_hub_variable_listener = Mock()
    hub.set_hub_variable = AsyncMock()
    return hub


@pytest.mark.asyncio
async def test_variable_entity_types_and_writes() -> None:
    hub = make_hub()
    integer = HubitatVariableNumber(
        hub, HubVariable({"name": "Counter", "type": "integer", "value": 2})
    )
    boolean = HubitatVariableSwitch(
        hub, HubVariable({"name": "Enabled", "type": "boolean", "value": "false"})
    )
    text = HubitatVariableText(
        hub, HubVariable({"name": "Message", "type": "string", "value": "hello"})
    )
    date_time = HubitatVariableDateTime(
        hub,
        HubVariable(
            {"name": "When", "type": "datetime", "value": "2026-09-04T12:30:00"}
        ),
    )

    assert integer.native_value == 2
    assert boolean.is_on is False
    assert text.native_value == "hello"
    assert date_time.native_value == datetime(2026, 9, 4, 12, 30)

    with (
        patch.object(integer, "async_write_ha_state"),
        patch.object(boolean, "async_write_ha_state"),
        patch.object(text, "async_write_ha_state"),
        patch.object(date_time, "async_write_ha_state"),
    ):
        await integer.async_set_native_value(3)
        await boolean.async_turn_on()
        await text.async_set_value("updated")
        await date_time.async_set_value(datetime(2026, 9, 5, 8, 0))

    assert hub.set_hub_variable.await_args_list == [
        (("Counter", "3"),),
        (("Enabled", "true"),),
        (("Message", "updated"),),
        (("When", "2026-09-05T08:00:00"),),
    ]
