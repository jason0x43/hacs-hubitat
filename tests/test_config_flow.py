from asyncio import Future
from collections.abc import Awaitable
from typing import Any
from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import pytest
import voluptuous as vol

from custom_components.hubitat.const import (
    H_CONF_APP_ID,
    H_CONF_HUB_ID,
    H_CONF_LEGACY_LIGHT_NAME_HEURISTIC,
    H_CONF_SERVER_PORT,
    H_CONF_SYNC_AREAS,
    H_CONF_SYNC_DEVICES,
    TEMP_C,
    TEMP_F,
)
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST, CONF_TEMPERATURE_UNIT
from homeassistant.helpers.selector import SelectSelector, SelectSelectorMode


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


def test_new_config_defaults_to_synchronizing_devices() -> None:
    """New config entries opt into Maker API device synchronization."""
    from custom_components.hubitat.config_flow import CONFIG_SCHEMA

    config = CONFIG_SCHEMA(
        {
            CONF_HOST: "hub.local",
            H_CONF_APP_ID: "123",
            CONF_ACCESS_TOKEN: "token",
        }
    )

    assert config[H_CONF_SYNC_DEVICES] is True


def test_temperature_unit_uses_dropdown_selector() -> None:
    """Temperature unit selection is shown as a dropdown."""
    from custom_components.hubitat.config_flow import CONFIG_SCHEMA

    temperature_key = next(
        key for key in CONFIG_SCHEMA.schema if key.schema == CONF_TEMPERATURE_UNIT
    )
    selector = CONFIG_SCHEMA.schema[temperature_key]

    assert isinstance(selector, SelectSelector)
    assert selector.config["options"] == [TEMP_F, TEMP_C]
    assert selector.config["mode"] == SelectSelectorMode.DROPDOWN
    assert selector.config["translation_key"] == "temperature_unit"

    data = CONFIG_SCHEMA(
        {CONF_HOST: "hub.local", H_CONF_APP_ID: "123", CONF_ACCESS_TOKEN: "token"}
    )
    assert CONF_TEMPERATURE_UNIT not in data


def test_options_schema_keeps_saved_temperature_unit() -> None:
    """Prepopulate options with an explicit saved temperature unit only."""
    from custom_components.hubitat.config_flow import _temperature_unit_option

    entry = Mock()
    entry.data = {CONF_TEMPERATURE_UNIT: "F"}
    entry.options = {CONF_TEMPERATURE_UNIT: "C"}

    schema = vol.Schema({_temperature_unit_option(entry): str})

    assert schema({})[CONF_TEMPERATURE_UNIT] == "C"


@pytest.mark.asyncio
async def test_options_update_finishes_from_the_first_form() -> None:
    """Saving ordinary options does not enter device management steps."""
    from custom_components.hubitat.config_flow import HubitatOptionsFlow

    entry = Mock()
    entry.data = {
        CONF_HOST: "hub.local",
        H_CONF_APP_ID: "123",
        CONF_ACCESS_TOKEN: "old-token",
    }
    entry.options = {"device_type_overrides": {"6": "light"}}
    flow = HubitatOptionsFlow(entry)
    flow.hass = Mock()
    user_input: dict[str, Any] = {
        CONF_HOST: "hub.local",
        H_CONF_APP_ID: "",
        CONF_ACCESS_TOKEN: "new-token",
        H_CONF_SERVER_PORT: None,
        "server_url": None,
        "server_ssl_cert": None,
        "server_ssl_key": None,
        CONF_TEMPERATURE_UNIT: "F",
        H_CONF_SYNC_DEVICES: False,
        H_CONF_SYNC_AREAS: False,
    }

    with (
        patch("custom_components.hubitat.config_flow._validate_input", AsyncMock()),
        patch.object(
            HubitatOptionsFlow,
            "config_entry",
            new_callable=PropertyMock,
            return_value=entry,
        ),
        patch.object(
            flow, "async_create_entry", return_value={"type": "create_entry"}
        ) as create_entry,
    ):
        result = await flow.async_step_user(user_input)

    assert result == {"type": "create_entry"}
    flow.hass.config_entries.async_update_entry.assert_called_once()
    create_entry.assert_called_once_with(
        title="",
        data={
            CONF_HOST: "hub.local",
            H_CONF_SERVER_PORT: None,
            "server_url": None,
            "server_ssl_cert": None,
            "server_ssl_key": None,
            CONF_TEMPERATURE_UNIT: "F",
            H_CONF_SYNC_DEVICES: False,
            H_CONF_SYNC_AREAS: False,
            "device_type_overrides": {"6": "light"},
        },
    )


@pytest.mark.asyncio
async def test_async_migrate_entry_v1_to_v2() -> None:
    """Test migration from config entry version 1 to version 2."""
    from custom_components.hubitat import async_migrate_entry

    # Create a mock config entry at version 1
    mock_entry = Mock()
    mock_entry.version = 1
    mock_entry.minor_version = 1
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
    assert call_args.kwargs["minor_version"] == 2
    assert new_data[H_CONF_LEGACY_LIGHT_NAME_HEURISTIC] is True

    # Check unique_id was set
    assert call_args.kwargs["unique_id"] == "abcd1234"


@pytest.mark.asyncio
async def test_async_migrate_entry_no_token() -> None:
    """Test migration fails gracefully when no token is present."""
    from custom_components.hubitat import async_migrate_entry

    mock_entry = Mock()
    mock_entry.version = 1
    mock_entry.minor_version = 1
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
async def test_async_migrate_entry_preserves_existing_unique_id() -> None:
    """A minor migration must not clear the existing config entry unique ID."""
    from custom_components.hubitat import async_migrate_entry

    mock_entry = Mock()
    mock_entry.version = 2
    mock_entry.minor_version = 1
    mock_entry.data = {CONF_ACCESS_TOKEN: "token"}
    mock_hass = Mock()
    mock_hass.config_entries.async_update_entry = Mock()

    assert await async_migrate_entry(mock_hass, mock_entry) is True
    assert (
        "unique_id" not in mock_hass.config_entries.async_update_entry.call_args.kwargs
    )


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

    mock_entity_int = Mock()
    mock_entity_int.unique_id = 42

    mock_ereg.entities = {
        "sensor.temp": mock_entity_old,
        "switch.light": mock_entity_new,
        "binary_sensor.motion": mock_entity_other,
        "sensor.int_id": mock_entity_int,
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
