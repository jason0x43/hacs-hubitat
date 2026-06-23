from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.hubitat.hubitatmaker import DeviceAttribute
from custom_components.hubitat.hubitatmaker.types import Attribute
from custom_components.hubitat.select import HubitatModeSelect, async_setup_entry


def test_mode_select() -> None:
    hub = Mock(id="hub", modes=["Day", "Night"], set_mode=AsyncMock())
    device = Mock(
        id="hub",
        name="Hub",
        label="Hub",
        attributes={
            DeviceAttribute.MODE: Attribute(
                {
                    "name": DeviceAttribute.MODE,
                    "currentValue": "Day",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        },
    )
    select = HubitatModeSelect(hub=hub, device=device)

    assert select.current_option == "Day"
    assert select.options == ["Day", "Night"]
    assert select.device_attrs == (DeviceAttribute.MODE,)


@pytest.mark.asyncio
async def test_mode_select_command_and_setup() -> None:
    hub = Mock(
        id="hub",
        mode_supported=True,
        modes=["Day"],
        set_mode=AsyncMock(),
        add_entities=Mock(),
    )
    hub.device = Mock(id="hub", name="Hub", label="Hub", attributes={})
    select = HubitatModeSelect(hub=hub, device=hub.device)
    await select.async_select_option("Day")
    hub.set_mode.assert_awaited_once_with("Day")

    add_entities = Mock()
    with patch("custom_components.hubitat.select.get_hub", return_value=hub):
        await async_setup_entry(Mock(), Mock(entry_id="entry"), add_entities)
    hub.add_entities.assert_called_once()
    add_entities.assert_called_once()

    hub.mode_supported = False
    hub.add_entities.reset_mock()
    add_entities.reset_mock()
    with patch("custom_components.hubitat.select.get_hub", return_value=hub):
        await async_setup_entry(Mock(), Mock(entry_id="entry"), add_entities)
    hub.add_entities.assert_not_called()
