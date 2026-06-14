from typing import Literal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.hubitat.alarm_control_panel import (
    HubitatSecurityKeypad,
    async_setup_entry,
    is_security_keypad,
)
from custom_components.hubitat.hubitatmaker import (
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
    DeviceState,
)
from custom_components.hubitat.hubitatmaker.types import Attribute
from homeassistant.components.alarm_control_panel.const import (
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)


def attr(
    name: DeviceAttribute,
    value: str,
    data_type: Literal["STRING", "JSON_OBJECT"] = "STRING",
) -> Attribute:
    return Attribute(
        {
            "name": name,
            "currentValue": value,
            "dataType": data_type,
            "unit": None,
        }
    )


def create_keypad() -> tuple[HubitatSecurityKeypad, Mock]:
    hub = Mock(id="hub", send_command=AsyncMock())
    device = Mock(
        id="keypad",
        name="Keypad",
        label="Keypad",
        commands={DeviceCommand.ARM_NIGHT},
        capabilities={DeviceCapability.SECURITY_KEYPAD, DeviceCapability.ALARM},
        attributes={
            DeviceAttribute.SECURITY_KEYPAD: attr(
                DeviceAttribute.SECURITY_KEYPAD, DeviceState.ARMED_HOME
            ),
            DeviceAttribute.CODE_LENGTH: attr(DeviceAttribute.CODE_LENGTH, "4"),
            DeviceAttribute.MAX_CODES: attr(DeviceAttribute.MAX_CODES, "10"),
            DeviceAttribute.ENTRY_DELAY: attr(DeviceAttribute.ENTRY_DELAY, "15"),
            DeviceAttribute.EXIT_DELAY: attr(DeviceAttribute.EXIT_DELAY, "30"),
            DeviceAttribute.ALARM: attr(DeviceAttribute.ALARM, "off"),
            DeviceAttribute.CODE_CHANGED: attr(DeviceAttribute.CODE_CHANGED, "Alice"),
            DeviceAttribute.LOCK_CODES: attr(
                DeviceAttribute.LOCK_CODES, '{"1":{"name":"Alice"}}', "JSON_OBJECT"
            ),
        },
    )
    return HubitatSecurityKeypad(hub=hub, device=device), hub


@pytest.mark.asyncio
async def test_keypad_state_and_commands() -> None:
    keypad, hub = create_keypad()
    assert keypad.alarm_state == AlarmControlPanelState.ARMED_HOME
    assert keypad.code_format == CodeFormat.NUMBER
    assert keypad.changed_by == "Alice"
    assert keypad.code_length == 4
    assert keypad.max_codes == 10
    assert keypad.entry_delay == 15
    assert keypad.exit_delay == 30
    assert keypad.codes == {"1": {"name": "Alice"}}
    assert keypad.supported_features & AlarmControlPanelEntityFeature.ARM_NIGHT
    assert keypad.supported_features & AlarmControlPanelEntityFeature.TRIGGER

    await keypad.async_alarm_disarm()
    await keypad.async_alarm_arm_away()
    await keypad.async_alarm_arm_home()
    await keypad.async_alarm_trigger()
    await keypad.set_entry_delay(5)
    await keypad.set_exit_delay(10)
    await keypad.clear_code(1)
    await keypad.set_code(2, "1234", "Bob")
    await keypad.set_code(3, "5678", None)
    await keypad.set_code_length(6)

    assert hub.send_command.await_count == 10


def test_keypad_detection_and_setup() -> None:
    assert is_security_keypad(Mock(capabilities={DeviceCapability.SECURITY_KEYPAD}))
    assert not is_security_keypad(Mock(capabilities=set()))


@pytest.mark.asyncio
async def test_keypad_setup_entry() -> None:
    with patch(
        "custom_components.hubitat.alarm_control_panel.create_and_add_entities"
    ) as create:
        await async_setup_entry(Mock(), Mock(), Mock())
    create.assert_called_once()
