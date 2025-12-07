# pyright: reportAny=false, reportPrivateUsage=false
# pyright: reportUnknownLambdaType=false, reportUnknownArgumentType=false

from asyncio import Future
from collections.abc import Awaitable
from unittest.mock import Mock, patch

import pytest

from custom_components.hubitat.const import H_CONF_APP_ID, H_CONF_HUB_ID
from homeassistant.const import CONF_ACCESS_TOKEN


@patch("custom_components.hubitat.config_flow.HubitatHub")
@pytest.mark.asyncio
async def test_validate_input(HubitatHub: Mock) -> None:
    check_called = False

    def check_config() -> Awaitable[None]:
        nonlocal check_called
        check_called = True
        future: Future[None] = Future()
        future.set_result(None)
        return future

    HubitatHub.return_value.check_config = check_config

    from custom_components.hubitat import config_flow

    with pytest.raises(KeyError):
        _ = await config_flow._validate_input({})
    with pytest.raises(KeyError):
        _ = await config_flow._validate_input({"host": "host"})
    with pytest.raises(KeyError):
        _ = await config_flow._validate_input({"host": "host", "app_id": "app_id"})
    _ = await config_flow._validate_input(
        {
            "host": "host",
            "app_id": "app_id",
            "access_token": "token",
            "server_port": 0,
            "server_url": None,
        }
    )
    assert check_called


@pytest.mark.asyncio
async def test_async_migrate_entry_v1_to_v2() -> None:
    """Test migration from config entry version 1 to version 2."""
    from custom_components.hubitat import async_migrate_entry

    # Create a mock config entry at version 1
    mock_entry = Mock()
    mock_entry.version = 1
    mock_entry.data = {
        CONF_ACCESS_TOKEN: "abcd1234efgh5678",
        H_CONF_APP_ID: "123",
    }

    # Create a mock hass
    mock_hass = Mock()
    mock_hass.config_entries = Mock()
    mock_hass.config_entries.async_update_entry = Mock()

    # Run migration
    result = await async_migrate_entry(mock_hass, mock_entry)

    # Verify migration succeeded
    assert result is True

    # Verify async_update_entry was called with correct args
    mock_hass.config_entries.async_update_entry.assert_called_once()
    call_args = mock_hass.config_entries.async_update_entry.call_args

    # Check the new data includes hub_id
    new_data = call_args.kwargs["data"]
    assert H_CONF_HUB_ID in new_data
    assert new_data[H_CONF_HUB_ID] == "abcd1234"  # First 8 chars of token

    # Check version was updated
    assert call_args.kwargs["version"] == 2

    # Check unique_id was set
    assert call_args.kwargs["unique_id"] == "abcd1234"


@pytest.mark.asyncio
async def test_async_migrate_entry_no_token() -> None:
    """Test migration fails gracefully when no token is present."""
    from custom_components.hubitat import async_migrate_entry

    mock_entry = Mock()
    mock_entry.version = 1
    mock_entry.data = {
        H_CONF_APP_ID: "123",
        # No access token
    }

    mock_hass = Mock()
    mock_hass.config_entries = Mock()
    mock_hass.config_entries.async_update_entry = Mock()

    result = await async_migrate_entry(mock_hass, mock_entry)

    # Migration should fail without a token
    assert result is False


@pytest.mark.asyncio
async def test_migrate_entity_unique_ids() -> None:
    """Test entity unique ID migration from token-hash format to hub-id format."""
    from custom_components.hubitat.hub import _migrate_entity_unique_ids
    from custom_components.hubitat.util import get_token_hash

    # Create mock entity registry
    mock_ereg = Mock()
    old_token = "abcd1234efgh5678"
    old_hash = get_token_hash(old_token)
    hub_id = "abcd1234"

    # Create mock entities - one with old format, one with new format
    mock_entity_old = Mock()
    mock_entity_old.unique_id = f"{old_hash}::42"

    mock_entity_new = Mock()
    mock_entity_new.unique_id = f"{hub_id}::99"

    mock_entity_other = Mock()
    mock_entity_other.unique_id = "some_other_format"

    mock_ereg.entities = {
        "sensor.temp": mock_entity_old,
        "switch.light": mock_entity_new,
        "binary_sensor.motion": mock_entity_other,
    }
    mock_ereg.async_update_entity = Mock()

    mock_hass = Mock()

    with patch(
        "custom_components.hubitat.hub.entity_registry.async_get",
        return_value=mock_ereg,
    ):
        _migrate_entity_unique_ids(mock_hass, hub_id, old_token)

    # Only the old format entity should be updated
    mock_ereg.async_update_entity.assert_called_once_with(
        "sensor.temp", new_unique_id=f"{hub_id}::42"
    )


def test_hub_id_with_stored_hub_id() -> None:
    """Test Hub.id returns stored hub_id when available."""
    from custom_components.hubitat.hub import Hub

    mock_entry = Mock()
    mock_entry.data = {
        H_CONF_HUB_ID: "stored_id",
        H_CONF_APP_ID: "123",
        CONF_ACCESS_TOKEN: "token123abc",
    }
    mock_entry.options = {}

    mock_hubitat_hub = Mock()
    mock_hubitat_hub.token = "token123abc"

    # Create Hub instance directly (bypassing factory method)
    with patch.object(Hub, "__init__", lambda self, *args, **kwargs: None):
        hub = Hub.__new__(Hub)
        hub.config_entry = mock_entry
        hub._hub = mock_hubitat_hub

    assert hub.id == "stored_id"


def test_hub_id_fallback_to_token() -> None:
    """Test Hub.id falls back to token-derived ID when hub_id not stored."""
    from custom_components.hubitat.hub import Hub

    mock_entry = Mock()
    mock_entry.data = {
        # No H_CONF_HUB_ID
        H_CONF_APP_ID: "123",
        CONF_ACCESS_TOKEN: "token123abc",
    }
    mock_entry.options = {}

    mock_hubitat_hub = Mock()
    mock_hubitat_hub.token = "token123abc"

    with patch.object(Hub, "__init__", lambda self, *args, **kwargs: None):
        hub = Hub.__new__(Hub)
        hub.config_entry = mock_entry
        hub._hub = mock_hubitat_hub

    # Should return first 8 chars of token
    assert hub.id == "token123"


def test_get_hub_device_id_uses_hub_id() -> None:
    """Test get_hub_device_id uses hub.id property."""
    from custom_components.hubitat.util import get_hub_device_id

    mock_hub = Mock()
    mock_hub.id = "my_hub_id"

    result = get_hub_device_id(mock_hub, "device_42")
    assert result == "my_hub_id::device_42"

    mock_device = Mock()
    mock_device.id = "device_99"
    result = get_hub_device_id(mock_hub, mock_device)
    assert result == "my_hub_id::device_99"
