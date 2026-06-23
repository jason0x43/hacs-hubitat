from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.hubitat import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.hubitat.const import H_CONF_HUBITAT_EVENT, PLATFORMS


@pytest.mark.asyncio
async def test_legacy_setup() -> None:
    assert await async_setup(Mock(), {}) is True


@pytest.mark.asyncio
async def test_setup_entry_connected() -> None:
    hub = Mock(
        id="hub",
        is_connected=True,
        async_connect=AsyncMock(),
        async_update_device_registry=Mock(),
        mark_platforms_setup=Mock(),
        stop=Mock(),
    )
    hass = Mock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    entry = Mock(entry_id="entry", title="Hubitat (aa:bb:cc:dd:ee:ff)")

    with (
        patch("custom_components.hubitat.get_domain_data", return_value={}),
        patch(
            "custom_components.hubitat.Hub.create_offline",
            AsyncMock(return_value=hub),
        ),
        patch("custom_components.hubitat.async_register_services") as register,
    ):
        assert await async_setup_entry(hass, entry) is True

    hub.async_connect.assert_awaited_once()
    hub.async_update_device_registry.assert_called_once()
    hub.mark_platforms_setup.assert_called_once()
    register.assert_called_once_with(hass, entry)
    hass.bus.fire.assert_called_once_with(H_CONF_HUBITAT_EVENT, {"name": "ready"})
    hass.config_entries.async_update_entry.assert_called_once_with(
        entry, title="Hubitat (hub)"
    )


@pytest.mark.asyncio
async def test_setup_entry_offline_schedules_retry() -> None:
    hub = Mock(
        id="hub",
        is_connected=False,
        async_connect=AsyncMock(side_effect=ConnectionError),
        mark_platforms_setup=Mock(),
        set_retry_task_unsub=Mock(),
        stop=Mock(),
    )
    hass = Mock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.async_create_task.side_effect = lambda coroutine: coroutine.close()
    entry = Mock(entry_id="entry", title="Hubitat")
    unsub = Mock()

    with (
        patch("custom_components.hubitat.get_domain_data", return_value={}),
        patch(
            "custom_components.hubitat.Hub.create_offline",
            AsyncMock(return_value=hub),
        ),
        patch(
            "custom_components.hubitat.async_track_time_interval",
            return_value=unsub,
        ),
        patch("custom_components.hubitat.async_register_services"),
    ):
        assert await async_setup_entry(hass, entry) is True

    hass.async_create_task.assert_called_once()
    hub.set_retry_task_unsub.assert_called_once_with(unsub)


@pytest.mark.asyncio
async def test_unload_entry() -> None:
    hub = Mock(
        get_unsetup_platforms=Mock(return_value=("select",)),
        stop=Mock(),
        unload=AsyncMock(),
    )
    hass = Mock()
    hass.config_entries.async_forward_entry_unload = AsyncMock(return_value=True)
    domain_data = {"entry": hub}
    entry = Mock(entry_id="entry")

    with (
        patch("custom_components.hubitat.async_remove_services") as remove,
        patch("custom_components.hubitat.get_hub", return_value=hub),
        patch("custom_components.hubitat.get_domain_data", return_value=domain_data),
    ):
        assert await async_unload_entry(hass, entry) is True

    remove.assert_called_once_with(hass, entry)
    hub.stop.assert_called_once()
    hub.unload.assert_awaited_once()
    assert "entry" not in domain_data
    unloaded = {
        item.args[1]
        for item in hass.config_entries.async_forward_entry_unload.call_args_list
    }
    assert unloaded == {platform for platform in PLATFORMS if platform != "select"}
