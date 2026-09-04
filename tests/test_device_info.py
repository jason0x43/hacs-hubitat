from unittest.mock import Mock, patch

from custom_components.hubitat.device import get_device_info


def test_get_device_info_uses_via_device_id_when_supported() -> None:
    hub = Mock(id="hub")
    hub.config_entry.entry_id = "entry"
    device = Mock(id="device", label="Device", room="Office", type="Switch")

    with patch(
        "custom_components.hubitat.device.device_registry.async_get_device_id_by_identifier",
        return_value="registry-hub-id",
    ) as get_device_id:
        info = get_device_info(hub, device)

    assert info["via_device_id"] == "registry-hub-id"
    get_device_id.assert_called_once_with(
        hub.hass,
        ("hubitat", "hub"),
        config_entry_id="entry",
    )


def test_get_device_info_omits_via_device_when_hub_is_not_registered() -> None:
    hub = Mock(id="hub")
    hub.config_entry.entry_id = "entry"
    device = Mock(id="device", label="Device", room="Office", type="Switch")

    with patch(
        "custom_components.hubitat.device.device_registry.async_get_device_id_by_identifier",
        side_effect=ValueError,
    ):
        info = get_device_info(hub, device)

    assert dict(info)["via_device"] == ("hubitat", "hub")
