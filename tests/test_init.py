import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.hubitat import (
    _async_connect_loop,
    _cancel_connect_task,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.hubitat.const import H_CONF_HUBITAT_EVENT, PLATFORMS


@pytest.mark.asyncio
async def test_legacy_setup() -> None:
    assert await async_setup(Mock(), {}) is True


@pytest.mark.asyncio
async def test_setup_entry_schedules_background_task() -> None:
    hub = Mock(
        id="hub",
        mark_platforms_setup=Mock(),
        set_connect_task=Mock(),
    )
    hass = Mock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    mock_task = Mock(spec=asyncio.Task)

    def mock_create_bg_task(_hass, target_coro, **kwargs):
        target_coro.close()  # Prevent RuntimeWarning: coroutine was never awaited
        return mock_task

    entry = Mock(
        entry_id="entry_123",
        title="Hubitat (aa:bb:cc:dd:ee:ff)",
        async_create_background_task=Mock(side_effect=mock_create_bg_task),
    )

    with (
        patch("custom_components.hubitat.get_domain_data", return_value={}),
        patch(
            "custom_components.hubitat.Hub.create_offline",
            AsyncMock(return_value=hub),
        ),
        patch("custom_components.hubitat.async_register_services") as register,
    ):
        assert await async_setup_entry(hass, entry) is True

    hass.config_entries.async_update_entry.assert_called_once_with(
        entry, title="Hubitat (hub)"
    )

    hub.mark_platforms_setup.assert_called_once()
    register.assert_called_once_with(hass, entry)

    entry.async_create_background_task.assert_called_once()
    _, kwargs = entry.async_create_background_task.call_args
    assert kwargs.get("name") == "hubitat_connect_entry_123"
    assert kwargs.get("eager_start") is False

    hub.set_connect_task.assert_called_once_with(mock_task)


@pytest.mark.asyncio
async def test_connect_loop_retries_until_connected() -> None:
    hass = Mock()
    Mock(title="Hubitat (abc12345)")
    hub = Mock(
        id="abc12345",
        async_connect=AsyncMock(
            side_effect=[ConnectionError("down"), asyncio.TimeoutError(), None]
        ),
        set_connected=Mock(),
    )

    with patch("custom_components.hubitat.RETRY_CONNECT_INTERVAL", timedelta(0)):
        await _async_connect_loop(hass, hub)

    assert hub.async_connect.await_count == 3
    assert hub.set_connected.call_count == 2
    hass.bus.fire.assert_called_once_with(H_CONF_HUBITAT_EVENT, {"name": "ready"})


@pytest.mark.asyncio
async def test_connect_loop_does_not_swallow_cancellation() -> None:
    started = asyncio.Event()

    async def blocked() -> None:
        started.set()
        await asyncio.Event().wait()

    hub = Mock(async_connect=AsyncMock(side_effect=blocked), set_connected=Mock())
    task = asyncio.create_task(_async_connect_loop(Mock(), hub))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    hub.set_connected.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_connect_task_cancels_and_awaits() -> None:
    task = asyncio.create_task(asyncio.sleep(3600))
    hub = Mock(get_connect_task=Mock(return_value=task))

    await _cancel_connect_task(hub)

    assert task.cancelled()


@pytest.mark.asyncio
async def test_cancel_connect_task_noop_when_empty_or_done() -> None:
    hub_none = Mock(get_connect_task=Mock(return_value=None))
    await _cancel_connect_task(hub_none)

    done_task = asyncio.create_task(asyncio.sleep(0))
    await done_task
    hub_done = Mock(get_connect_task=Mock(return_value=done_task))
    await _cancel_connect_task(hub_done)


@pytest.mark.asyncio
async def test_unload_entry() -> None:
    hub = Mock(
        get_connect_task=Mock(return_value=None),
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
