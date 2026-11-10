from unittest.mock import Mock, patch

from custom_components.hubitat.const import DOMAIN
from custom_components.hubitat.device import get_device_info
from custom_components.hubitat.hub import _update_device_rooms

# create=True lets these run on Home Assistant versions without the lookup API.
_DEVICE_ID_LOOKUP = (
    "custom_components.hubitat.device.device_registry.async_get_device_id_by_identifier"
)


def _create_hub_and_device() -> tuple[Mock, Mock]:
    hub = Mock(id="hub")
    hub.config_entry.entry_id = "entry"
    device = Mock(id="device", label="Device", room="Office", type="Switch")
    return hub, device


def test_get_device_info_uses_via_device_id_when_supported() -> None:
    hub, device = _create_hub_and_device()

    with (
        patch("custom_components.hubitat.device.HAS_DEVICE_ID_LOOKUP", True),
        patch(_DEVICE_ID_LOOKUP, create=True, return_value="registry-hub-id") as get_id,
    ):
        info = get_device_info(hub, device)

    assert dict(info)["via_device_id"] == "registry-hub-id"
    assert "via_device" not in dict(info)
    get_id.assert_called_once_with(
        hub.hass,
        ("hubitat", "hub"),
        config_entry_id="entry",
    )


def test_get_device_info_omits_via_device_when_hub_is_not_registered() -> None:
    hub, device = _create_hub_and_device()

    with (
        patch("custom_components.hubitat.device.HAS_DEVICE_ID_LOOKUP", True),
        patch(_DEVICE_ID_LOOKUP, create=True, side_effect=ValueError),
    ):
        info = get_device_info(hub, device)

    assert "via_device" not in dict(info)
    assert "via_device_id" not in dict(info)


def test_get_device_info_uses_via_device_without_device_id_lookup() -> None:
    hub, device = _create_hub_and_device()

    with (
        patch("custom_components.hubitat.device.HAS_DEVICE_ID_LOOKUP", False),
        patch(_DEVICE_ID_LOOKUP, create=True) as get_id,
    ):
        info = get_device_info(hub, device)

    assert dict(info)["via_device"] == ("hubitat", "hub")
    assert "via_device_id" not in dict(info)
    get_id.assert_not_called()


def test_update_device_rooms_uses_config_entry_scoped_identifier_lookup() -> None:
    hass = Mock()
    hub = Mock(id="hub")
    hub.config_entry.entry_id = "entry"
    hub.devices = {
        "device": Mock(id="device", name="Device", room="Office"),
    }
    hass_device = Mock(area_id=None)
    dreg = Mock()
    dreg.devices = {}
    dreg.async_get_device_by_identifier.return_value = hass_device

    with (
        patch(
            "custom_components.hubitat.hub.device_registry.async_get", return_value=dreg
        ),
        patch("custom_components.hubitat.hub.area_registry.async_get"),
    ):
        _update_device_rooms(hub, hass)

    dreg.async_get_device_by_identifier.assert_called_once_with(
        (DOMAIN, "hub:device"), "entry"
    )
    dreg.async_get_device.assert_not_called()


def test_update_device_rooms_uses_legacy_lookup_when_needed() -> None:
    hass = Mock()
    hub = Mock(id="hub")
    hub.config_entry.entry_id = "entry"
    hub.devices = {
        "device": Mock(id="device", name="Device", room="Office"),
    }
    dreg = Mock(spec=["devices", "async_get_device", "async_update_device"])
    dreg.devices = {}
    dreg.async_get_device.return_value = Mock(area_id=None)

    with (
        patch(
            "custom_components.hubitat.hub.device_registry.async_get", return_value=dreg
        ),
        patch("custom_components.hubitat.hub.area_registry.async_get"),
    ):
        _update_device_rooms(hub, hass)

    dreg.async_get_device.assert_called_once_with({(DOMAIN, "hub:device")})
