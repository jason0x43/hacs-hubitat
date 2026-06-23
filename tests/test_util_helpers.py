from unittest.mock import Mock, patch

import pytest

from custom_components.hubitat.error import DeviceError
from custom_components.hubitat.helpers import (
    are_config_entries_loaded,
    get_device_entry_by_device_id,
    get_hub,
    get_hub_for_device,
)
from custom_components.hubitat.util import (
    get_device_identifiers,
    get_device_overrides,
    get_hub_short_id,
    get_hubitat_device_id,
    get_token_hash,
    to_display_name,
)
from homeassistant.config_entries import ConfigEntryState


def test_util_helpers() -> None:
    token = "secret"
    assert get_token_hash(token) == get_token_hash(token)
    assert len(get_token_hash(token)) == 64
    assert get_hub_short_id(Mock(token="abcdefghijk")) == "abcdefgh"

    entry = Mock(options={"device_type_overrides": {"1": "light"}})
    assert get_device_overrides(entry) == {"1": "light"}

    assert to_display_name("securityKeypad") == "Security keypad"
    assert to_display_name("SECURITYKeypad") == "Security keypad"
    assert to_display_name("security_keypad") == "Security keypad"

    assert get_device_identifiers("hub", "hub") == {("hubitat", "hub")}
    assert get_device_identifiers("hub", "device") == {("hubitat", "hub:device")}


def test_get_hubitat_device_id() -> None:
    device = Mock(id="device", identifiers={("other", "x"), ("hubitat", "hub:42")})
    assert get_hubitat_device_id(device) == "42"

    device.identifiers = {("hubitat", "42")}
    assert get_hubitat_device_id(device) == "42"

    device.identifiers = {("other", "42")}
    with pytest.raises(DeviceError):
        get_hubitat_device_id(device)


def test_helpers_find_devices_and_hubs() -> None:
    hass = Mock()
    device = Mock(id="device", config_entries={"missing", "loaded"})
    registry = Mock()
    registry.async_get.return_value = device

    loaded = Mock(state=ConfigEntryState.LOADED)
    hass.config_entries.async_get_entry.side_effect = lambda entry_id: (
        loaded if entry_id == "loaded" else None
    )

    with patch(
        "custom_components.hubitat.helpers.device_registry.async_get",
        return_value=registry,
    ):
        assert get_device_entry_by_device_id(hass, "device") is device
        assert are_config_entries_loaded(hass, "device") is False

        registry.async_get.return_value = None
        with pytest.raises(DeviceError):
            get_device_entry_by_device_id(hass, "bad")

    hub = Mock()
    with patch(
        "custom_components.hubitat.helpers.get_hub",
        side_effect=lambda _hass, entry_id: hub if entry_id == "loaded" else None,
    ):
        assert get_hub_for_device(hass, device) is hub

    with patch(
        "custom_components.hubitat.helpers.get_domain_data",
        return_value={"loaded": hub},
    ):
        assert get_hub(hass, "loaded") is hub
        assert get_hub(hass, "missing") is None
