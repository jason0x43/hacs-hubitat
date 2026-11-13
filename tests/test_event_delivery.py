from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.hubitat import event_delivery
from custom_components.hubitat.event_delivery import (
    CloudNotConnected,
    NoEventUrlAvailable,
    async_delete_cloudhook,
    async_get_event_url,
    async_listen_cloud_connected,
    can_deliver_cloud_events,
    is_cloud_host,
)
from homeassistant.helpers.network import NoURLAvailableError

CLOUD_HOST = "https://cloud.hubitat.com/api/abc-123/apps/1234"
WEBHOOK_PATH = "/api/webhook/hook-id"


def _hass(
    components: set[str] | None = None,
    api: Any = None,
) -> Mock:
    hass = Mock()
    hass.config.components = components or set()
    hass.config.api = api
    return hass


def _cloud(logged_in: bool = True, connected: bool = True) -> Mock:
    cloud = Mock()
    cloud.async_is_logged_in.return_value = logged_in
    cloud.async_is_connected.return_value = connected
    cloud.async_get_or_create_cloudhook = AsyncMock(
        return_value="https://hooks.nabu.casa/abc"
    )
    cloud.async_delete_cloudhook = AsyncMock()
    return cloud


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        (CLOUD_HOST, True),
        ("https://cloud.hubitat.com", True),
        ("10.0.1.99", False),
        ("http://10.0.1.99", False),
        ("hubitat.local", False),
        (None, False),
        ("", False),
    ],
)
def test_is_cloud_host(host: str | None, expected: bool) -> None:
    assert is_cloud_host(host) is expected


@pytest.mark.asyncio
async def test_event_url_uses_base_url_override() -> None:
    hass = _hass()
    url = await async_get_event_url(
        hass, "hook-id", CLOUD_HOST, "https://ha.example.com/"
    )
    assert url == f"https://ha.example.com{WEBHOOK_PATH}"


@pytest.mark.asyncio
async def test_local_hub_uses_internal_url() -> None:
    hass = _hass()
    with patch.object(
        event_delivery, "get_url", return_value="http://192.168.1.10:8123"
    ) as get_url:
        url = await async_get_event_url(hass, "hook-id", "10.0.1.99", None)

    assert url == f"http://192.168.1.10:8123{WEBHOOK_PATH}"
    assert get_url.call_args.kwargs["allow_external"] is False
    assert get_url.call_args.kwargs["allow_cloud"] is False


@pytest.mark.asyncio
async def test_local_hub_prefers_ip_over_mdns_name() -> None:
    api = SimpleNamespace(local_ip="192.168.1.10", port=8123, use_ssl=False)
    hass = _hass(api=api)
    with patch.object(
        event_delivery, "get_url", return_value="http://homeassistant.local:8123"
    ):
        url = await async_get_event_url(hass, "hook-id", "10.0.1.99", None)

    assert url == f"http://192.168.1.10:8123{WEBHOOK_PATH}"


@pytest.mark.asyncio
async def test_local_hub_does_not_use_cloudhook() -> None:
    cloud = _cloud()
    hass = _hass({"cloud"})
    with (
        patch.object(event_delivery, "_get_cloud", return_value=cloud),
        patch.object(event_delivery, "get_url", return_value="http://10.0.0.2:8123"),
    ):
        url = await async_get_event_url(hass, "hook-id", "10.0.1.99", None)

    assert url == f"http://10.0.0.2:8123{WEBHOOK_PATH}"
    cloud.async_get_or_create_cloudhook.assert_not_called()


@pytest.mark.asyncio
async def test_local_hub_without_url_raises() -> None:
    hass = _hass()
    with (
        patch.object(event_delivery, "get_url", side_effect=NoURLAvailableError),
        pytest.raises(NoEventUrlAvailable),
    ):
        _ = await async_get_event_url(hass, "hook-id", "10.0.1.99", None)


@pytest.mark.asyncio
async def test_cloud_hub_uses_cloudhook() -> None:
    cloud = _cloud()
    hass = _hass({"cloud"})
    with patch.object(event_delivery, "_get_cloud", return_value=cloud):
        url = await async_get_event_url(hass, "hook-id", CLOUD_HOST, None)

    assert url == "https://hooks.nabu.casa/abc"
    cloud.async_get_or_create_cloudhook.assert_awaited_once_with(hass, "hook-id")


@pytest.mark.asyncio
async def test_cloud_hub_waits_for_cloud_connection() -> None:
    cloud = _cloud(connected=False)
    hass = _hass({"cloud"})
    with (
        patch.object(event_delivery, "_get_cloud", return_value=cloud),
        pytest.raises(CloudNotConnected),
    ):
        _ = await async_get_event_url(hass, "hook-id", CLOUD_HOST, None)


@pytest.mark.asyncio
async def test_cloud_hub_without_cloud_uses_external_url() -> None:
    hass = _hass()
    with patch.object(
        event_delivery, "get_url", return_value="https://ha.example.com"
    ) as get_url:
        url = await async_get_event_url(hass, "hook-id", CLOUD_HOST, None)

    assert url == f"https://ha.example.com{WEBHOOK_PATH}"
    assert get_url.call_args.kwargs["allow_internal"] is False


@pytest.mark.asyncio
async def test_cloud_hub_without_public_url_raises() -> None:
    hass = _hass()
    with (
        patch.object(event_delivery, "get_url", side_effect=NoURLAvailableError),
        pytest.raises(NoEventUrlAvailable),
    ):
        _ = await async_get_event_url(hass, "hook-id", CLOUD_HOST, None)


def test_can_deliver_cloud_events() -> None:
    hass = _hass()
    assert can_deliver_cloud_events(hass, "https://ha.example.com") is True

    with patch.object(event_delivery, "_get_cloud", return_value=_cloud()):
        assert can_deliver_cloud_events(hass, None) is True

    with patch.object(event_delivery, "get_url", return_value="https://ha.example"):
        assert can_deliver_cloud_events(hass, None) is True

    with patch.object(event_delivery, "get_url", side_effect=NoURLAvailableError):
        assert can_deliver_cloud_events(hass, None) is False


def test_cloud_is_ignored_when_not_loaded() -> None:
    assert event_delivery._get_cloud(_hass()) is None


@pytest.mark.asyncio
async def test_delete_cloudhook() -> None:
    cloud = _cloud()
    hass = _hass({"cloud"})
    with patch.object(event_delivery, "_get_cloud", return_value=cloud):
        await async_delete_cloudhook(hass, "hook-id")
    cloud.async_delete_cloudhook.assert_awaited_once_with(hass, "hook-id")


@pytest.mark.asyncio
async def test_delete_cloudhook_ignores_errors_and_missing_cloud() -> None:
    cloud = _cloud()
    cloud.async_delete_cloudhook.side_effect = Exception("boom")
    hass = _hass({"cloud"})
    with patch.object(event_delivery, "_get_cloud", return_value=cloud):
        await async_delete_cloudhook(hass, "hook-id")

    # No cloud integration: nothing to delete
    await async_delete_cloudhook(_hass(), "hook-id")


@pytest.mark.asyncio
async def test_listen_cloud_connected() -> None:
    cloud = _cloud()
    cloud.CloudConnectionState = SimpleNamespace(
        CLOUD_CONNECTED="connected", CLOUD_DISCONNECTED="disconnected"
    )
    unsub = Mock()
    cloud.async_listen_connection_change.return_value = unsub
    target = AsyncMock()
    hass = _hass({"cloud"})

    with patch.object(event_delivery, "_get_cloud", return_value=cloud):
        result = async_listen_cloud_connected(hass, target)

    assert result is unsub
    handler = cloud.async_listen_connection_change.call_args.args[1]
    await handler("disconnected")
    target.assert_not_awaited()
    await handler("connected")
    target.assert_awaited_once()

    assert async_listen_cloud_connected(_hass(), target) is None
