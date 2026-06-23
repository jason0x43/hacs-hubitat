from typing import TypeVar
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from custom_components.hubitat.device import HubitatEntity
from custom_components.hubitat.hubitatmaker import DeviceAttribute, DeviceCommand
from custom_components.hubitat.hubitatmaker.types import Attribute
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


@pytest.mark.asyncio
async def test_switch_and_alarm_commands() -> None:
    from custom_components.hubitat.switch import (
        HubitatAlarm,
        HubitatPowerMeterSwitch,
        HubitatSwitch,
    )

    hub = Mock(token="token")
    device = Mock(
        id="device",
        name="Device",
        label="Device Switch",
        attributes={
            DeviceAttribute.SWITCH: Attribute(
                {
                    "name": DeviceAttribute.SWITCH,
                    "currentValue": "on",
                    "dataType": "STRING",
                    "unit": None,
                }
            ),
            DeviceAttribute.POWER: Attribute(
                {
                    "name": DeviceAttribute.POWER,
                    "currentValue": "12.5",
                    "dataType": "NUMBER",
                    "unit": "W",
                }
            ),
        },
    )
    switch = HubitatSwitch(hub=hub, device=device)
    power = HubitatPowerMeterSwitch(hub=hub, device=device)
    alarm = HubitatAlarm(hub=hub, device=device)
    switch.send_command = AsyncMock()  # type: ignore[method-assign]
    alarm.send_command = AsyncMock()  # type: ignore[method-assign]

    await switch.async_turn_on()
    await switch.async_turn_off()
    await alarm.async_turn_on()
    await alarm.siren_on()
    await alarm.strobe_on()

    assert power.current_power_w == 12.5
    switch.send_command.assert_has_awaits([call(DeviceCommand.ON), call("off")])
    assert alarm.send_command.await_count == 3
