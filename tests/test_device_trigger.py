from typing import cast
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.hubitat.const import (
    H_CONF_DOUBLE_TAPPED,
    H_CONF_HELD,
    H_CONF_PUSHED,
    H_CONF_SUBTYPE,
    H_CONF_UNLOCKED_WITH_CODE,
)
from custom_components.hubitat.device_trigger import (
    DeviceWrapper,
    async_attach_trigger,
    async_get_triggers,
    get_hubitat_device,
    get_lock_codes,
    get_trigger_subtypes,
    get_trigger_types,
    get_valid_subtypes,
)
from custom_components.hubitat.hubitatmaker import DeviceAttribute, DeviceCapability
from custom_components.hubitat.hubitatmaker.types import Attribute
from homeassistant.components.device_automation.exceptions import (
    InvalidDeviceAutomationConfig,
)
from homeassistant.const import CONF_DEVICE_ID, CONF_TYPE
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo


def attr(name: DeviceAttribute, value: str) -> Attribute:
    return Attribute(
        {"name": name, "currentValue": value, "dataType": "STRING", "unit": None}
    )


def test_trigger_types_and_subtypes() -> None:
    device = Mock(
        capabilities={
            DeviceCapability.DOUBLE_TAPABLE_BUTTON,
            DeviceCapability.HOLDABLE_BUTTON,
            DeviceCapability.PUSHABLE_BUTTON,
            DeviceCapability.LOCK,
        },
        attributes={
            DeviceAttribute.NUM_BUTTONS: attr(DeviceAttribute.NUM_BUTTONS, "2"),
            DeviceAttribute.LOCK_CODES: attr(
                DeviceAttribute.LOCK_CODES,
                '{"1":{"name":"Alice"},"2":{"name":"Bob"}}',
            ),
        },
    )

    assert get_trigger_types(device) == [
        H_CONF_DOUBLE_TAPPED,
        H_CONF_HELD,
        H_CONF_PUSHED,
        H_CONF_UNLOCKED_WITH_CODE,
    ]
    assert get_trigger_subtypes(device, H_CONF_PUSHED) == ["1", "2"]
    assert get_trigger_subtypes(device, H_CONF_UNLOCKED_WITH_CODE) == ["Alice", "Bob"]
    assert get_trigger_subtypes(device, "unknown") == []
    assert get_valid_subtypes(H_CONF_PUSHED) is not None
    assert get_valid_subtypes("unknown") is None

    device.attributes[DeviceAttribute.LOCK_CODES] = attr(
        DeviceAttribute.LOCK_CODES, "invalid"
    )
    assert get_lock_codes(device) == []


@pytest.mark.asyncio
async def test_get_and_attach_triggers() -> None:
    device = Mock(
        id="42",
        capabilities={DeviceCapability.PUSHABLE_BUTTON},
        attributes={
            DeviceAttribute.NUM_BUTTONS: attr(DeviceAttribute.NUM_BUTTONS, "2")
        },
    )
    hub = Mock(id="hub", devices={"42": device})
    wrapper = DeviceWrapper(device, hub)

    with patch(
        "custom_components.hubitat.device_trigger.get_hubitat_device",
        return_value=wrapper,
    ):
        triggers = await async_get_triggers(Mock(), "ha-device")
        assert [trigger[H_CONF_SUBTYPE] for trigger in triggers] == [
            "1",
            "2",
        ]

        attach = AsyncMock(return_value=Mock())
        with (
            patch(
                "custom_components.hubitat.device_trigger.event.async_attach_trigger",
                attach,
            ),
            patch(
                "custom_components.hubitat.device_trigger.event.TRIGGER_SCHEMA",
                side_effect=lambda config: config,
            ),
        ):
            await async_attach_trigger(
                Mock(),
                {
                    CONF_DEVICE_ID: "ha-device",
                    CONF_TYPE: H_CONF_PUSHED,
                    H_CONF_SUBTYPE: "1",
                },
                cast(TriggerActionType, Mock()),
                cast(TriggerInfo, Mock()),
            )
        event_data = attach.call_args.args[1]["event_data"]
        assert event_data == {
            "device_id": "42",
            "hub": "hub",
            "attribute": H_CONF_PUSHED,
            "value": "1",
        }

    with patch(
        "custom_components.hubitat.device_trigger.get_hubitat_device",
        return_value=None,
    ):
        assert await async_get_triggers(Mock(), "missing") == []
        with pytest.raises(InvalidDeviceAutomationConfig):
            await async_attach_trigger(
                Mock(),
                {CONF_DEVICE_ID: "missing"},
                Mock(),
                cast(TriggerInfo, Mock()),
            )


def test_get_hubitat_device() -> None:
    entry = Mock()
    hub = Mock(devices={"42": Mock()})
    with (
        patch(
            "custom_components.hubitat.device_trigger.get_device_entry_by_device_id",
            return_value=entry,
        ),
        patch(
            "custom_components.hubitat.device_trigger.get_hubitat_device_id",
            return_value="42",
        ),
        patch(
            "custom_components.hubitat.device_trigger.get_hub_for_device",
            return_value=hub,
        ),
    ):
        wrapper = get_hubitat_device(Mock(), "device")
        assert wrapper is not None
        assert wrapper.hub is hub

    with (
        patch(
            "custom_components.hubitat.device_trigger.get_device_entry_by_device_id",
            return_value=entry,
        ),
        patch(
            "custom_components.hubitat.device_trigger.get_hubitat_device_id",
            return_value="42",
        ),
        patch(
            "custom_components.hubitat.device_trigger.get_hub_for_device",
            return_value=None,
        ),
    ):
        assert get_hubitat_device(Mock(), "device") is None
