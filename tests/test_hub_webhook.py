from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.hubitat import hub as hub_module
from custom_components.hubitat.const import (
    H_CONF_SERVER_URL,
    H_CONF_USE_EVENT_SERVER,
    H_CONF_WEBHOOK_ID,
)
from custom_components.hubitat.event_delivery import (
    CloudNotConnected,
    NoEventUrlAvailable,
)
from custom_components.hubitat.hub import Hub, uses_event_server

CLOUD_HOST = "https://cloud.hubitat.com/api/abc-123/apps/123"


def _entry(
    data: dict[str, Any] | None = None, options: dict[str, Any] | None = None
) -> Mock:
    entry = Mock()
    entry.entry_id = "entry-id"
    entry.data = {
        "host": "192.168.1.10",
        "app_id": "123",
        "access_token": "token",
        "hub_id": "hub12345",
        H_CONF_WEBHOOK_ID: "hook-id",
        H_CONF_USE_EVENT_SERVER: False,
        **(data or {}),
    }
    entry.options = options or {}
    entry.add_update_listener = Mock(return_value=Mock())
    return entry


def _create_hub(entry: Mock | None = None) -> tuple[Hub, Mock]:
    hass = Mock()
    hass.data = {}
    hass.config.config_dir = "/tmp"
    hubitat_hub = Mock()
    hubitat_hub.devices = {}
    hubitat_hub.set_event_url = AsyncMock()
    hubitat_hub.start_event_server = AsyncMock()
    hub = Hub(hass, entry or _entry(), 1, hubitat_hub, Mock())
    return hub, hubitat_hub


def _request(data: Any = None, error: Exception | None = None) -> Mock:
    request = Mock()
    if error is not None:
        request.json = AsyncMock(side_effect=error)
    else:
        request.json = AsyncMock(return_value=data)
    return request


def test_uses_event_server() -> None:
    assert uses_event_server(_entry()) is False
    assert uses_event_server(_entry({H_CONF_USE_EVENT_SERVER: True})) is True
    assert uses_event_server(_entry(options={H_CONF_USE_EVENT_SERVER: True})) is True
    # An entry without a webhook ID can only use the server
    assert uses_event_server(_entry({H_CONF_WEBHOOK_ID: None})) is True


@pytest.mark.parametrize(
    ("host", "options", "local_only"),
    [
        ("10.0.1.2", {}, True),
        ("10.0.1.2", {H_CONF_SERVER_URL: ""}, True),
        (CLOUD_HOST, {}, False),
        # A configured event URL may be on another network
        ("10.0.1.2", {H_CONF_SERVER_URL: "https://ha.example.com"}, False),
    ],
)
def test_register_webhook(host: str, options: dict[str, Any], local_only: bool) -> None:
    hub, _ = _create_hub(_entry({"host": host}, options))
    with patch.object(hub_module.webhook, "async_register") as register:
        hub.async_register_webhook()
        hub.async_register_webhook()

    register.assert_called_once()
    assert register.call_args.args[3] == "hook-id"
    assert register.call_args.kwargs["local_only"] is local_only
    assert register.call_args.kwargs["allowed_methods"] == ["POST"]

    with patch.object(hub_module.webhook, "async_unregister") as unregister:
        hub.async_unregister_webhook()
        hub.async_unregister_webhook()
    unregister.assert_called_once_with(hub.hass, "hook-id")


def test_event_server_entries_do_not_register_webhook() -> None:
    hub, _ = _create_hub(_entry({H_CONF_USE_EVENT_SERVER: True}))
    with patch.object(hub_module.webhook, "async_register") as register:
        hub.async_register_webhook()
    register.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_ignores_events_until_started() -> None:
    hub, hubitat_hub = _create_hub()
    event = {"content": {"deviceId": "1", "name": "switch", "value": "on"}}

    response = await hub._async_handle_webhook(hub.hass, "hook-id", _request(event))
    assert response is None
    hubitat_hub.process_event.assert_not_called()

    hub._accept_webhook_events = True
    _ = await hub._async_handle_webhook(hub.hass, "hook-id", _request(event))
    hubitat_hub.process_event.assert_called_once_with(event)

    hub.stop()
    _ = await hub._async_handle_webhook(hub.hass, "hook-id", _request(event))
    hubitat_hub.process_event.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "request_", [_request(error=ValueError("bad json")), _request(["not", "a", "dict"])]
)
async def test_webhook_rejects_invalid_events(request_: Mock) -> None:
    hub, hubitat_hub = _create_hub()
    hub._accept_webhook_events = True

    response = await hub._async_handle_webhook(hub.hass, "hook-id", request_)

    assert response is not None
    assert response.status == 400
    hubitat_hub.process_event.assert_not_called()


@pytest.mark.asyncio
async def test_update_event_url_sets_webhook_url() -> None:
    hub, hubitat_hub = _create_hub(
        _entry(options={H_CONF_SERVER_URL: "http://10.0.0.5:8123"})
    )
    with patch.object(
        hub_module, "async_get_event_url", AsyncMock(return_value="http://url")
    ) as get_event_url:
        await hub._async_update_event_url()

    get_event_url.assert_awaited_once_with(
        hub.hass, "hook-id", "192.168.1.10", "http://10.0.0.5:8123"
    )
    hubitat_hub.set_event_url.assert_awaited_once_with("http://url")


@pytest.mark.asyncio
async def test_update_event_url_skipped_for_event_server() -> None:
    hub, hubitat_hub = _create_hub(_entry({H_CONF_USE_EVENT_SERVER: True}))
    with patch.object(hub_module, "async_get_event_url", AsyncMock()) as get_url:
        await hub._async_update_event_url()
    get_url.assert_not_awaited()
    hubitat_hub.set_event_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_local_hub_falls_back_to_event_server_without_url() -> None:
    hub, hubitat_hub = _create_hub()
    with patch.object(
        hub_module,
        "async_get_event_url",
        AsyncMock(side_effect=NoEventUrlAvailable("nope")),
    ):
        await hub._async_update_event_url()
    hubitat_hub.set_event_url.assert_not_awaited()
    hubitat_hub.start_event_server.assert_awaited_once()


@pytest.mark.asyncio
async def test_cloud_hub_without_url_does_not_start_event_server() -> None:
    hub, hubitat_hub = _create_hub(_entry({"host": CLOUD_HOST}))
    with patch.object(
        hub_module,
        "async_get_event_url",
        AsyncMock(side_effect=NoEventUrlAvailable("nope")),
    ):
        await hub._async_update_event_url()
    hubitat_hub.set_event_url.assert_not_awaited()
    hubitat_hub.start_event_server.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_event_url_waits_for_cloud_connection() -> None:
    hub, hubitat_hub = _create_hub(_entry({"host": CLOUD_HOST}))
    # The hub has started but is still setting up platforms, so it isn't
    # marked connected yet.
    hub._accept_webhook_events = True
    hub._is_connected = False
    unsub = Mock()
    get_event_url = AsyncMock(
        side_effect=[CloudNotConnected("not yet"), "https://hooks.nabu.casa/abc"]
    )

    with (
        patch.object(hub_module, "async_get_event_url", get_event_url),
        patch.object(
            hub_module, "async_listen_cloud_connected", return_value=unsub
        ) as listen,
    ):
        await hub._async_update_event_url()
        hubitat_hub.set_event_url.assert_not_awaited()
        listen.assert_called_once()

        # A second failure doesn't add another listener
        on_connected = listen.call_args.args[1]
        await on_connected()

    unsub.assert_called_once()
    hubitat_hub.set_event_url.assert_awaited_once_with("https://hooks.nabu.casa/abc")


def test_stop_removes_cloud_listener() -> None:
    hub, _ = _create_hub()
    unsub = Mock()
    hub._unsub_cloud_listener = unsub
    hub.stop()
    unsub.assert_called_once()
    assert hub._unsub_cloud_listener is None


@pytest.mark.asyncio
async def test_cloud_callback_waits_while_hub_is_not_running() -> None:
    hub, hubitat_hub = _create_hub(_entry({"host": CLOUD_HOST}))
    unsub = Mock()
    with (
        patch.object(
            hub_module,
            "async_get_event_url",
            AsyncMock(side_effect=CloudNotConnected("not yet")),
        ),
        patch.object(
            hub_module, "async_listen_cloud_connected", return_value=unsub
        ) as listen,
    ):
        hub._accept_webhook_events = True
        await hub._async_update_event_url()
        on_connected = listen.call_args.args[1]

        hub._accept_webhook_events = False
        await on_connected()

    unsub.assert_not_called()
    hubitat_hub.set_event_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_cloud_callback_retries_failed_event_url_update() -> None:
    """A postURL failure after Home Assistant Cloud connects is retried."""
    entry = _entry({"host": CLOUD_HOST})
    hub, hubitat_hub = _create_hub(entry)
    hub._accept_webhook_events = True
    hubitat_hub.set_event_url.side_effect = [ConnectionError("offline"), None]
    get_event_url = AsyncMock(
        side_effect=[
            CloudNotConnected("not yet"),
            "https://hooks.nabu.casa/abc",
            "https://hooks.nabu.casa/abc",
        ]
    )
    cancel_retry = Mock()

    with (
        patch.object(hub_module, "async_get_event_url", get_event_url),
        patch.object(
            hub_module, "async_listen_cloud_connected", return_value=Mock()
        ) as listen,
        patch.object(
            hub_module, "async_call_later", return_value=cancel_retry
        ) as call_later,
    ):
        await hub._async_update_event_url()
        on_connected = listen.call_args.args[1]

        # The postURL request fails, so a retry is scheduled
        await on_connected()
        call_later.assert_called_once()
        assert call_later.call_args.args[1] == hub_module.EVENT_URL_RETRY_DELAY

        # When the retry fires, it runs the update in a background task
        retry = call_later.call_args.args[2]
        retry(None)
        create_task = entry.async_create_background_task
        create_task.assert_called_once()
        await create_task.call_args.args[1]

    assert hubitat_hub.set_event_url.await_count == 2
    hubitat_hub.set_event_url.assert_awaited_with("https://hooks.nabu.casa/abc")
    # The retry succeeded, so no new one was scheduled
    call_later.assert_called_once()
    assert hub._cancel_event_url_retry is None


def test_stop_cancels_event_url_retry() -> None:
    hub, _ = _create_hub()
    cancel_retry = Mock()
    hub._cancel_event_url_retry = cancel_retry

    hub.stop()

    cancel_retry.assert_called_once()
    assert hub._cancel_event_url_retry is None


def test_event_url_retry_is_skipped_when_hub_stopped() -> None:
    entry = _entry()
    hub, _ = _create_hub(entry)
    with patch.object(hub_module, "async_call_later", return_value=Mock()) as later:
        hub._schedule_event_url_retry()
        hub._schedule_event_url_retry()
    later.assert_called_once()

    retry = later.call_args.args[2]
    hub._accept_webhook_events = False
    retry(None)
    entry.async_create_background_task.assert_not_called()
    assert hub._cancel_event_url_retry is None
