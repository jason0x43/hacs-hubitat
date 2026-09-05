from unittest.mock import Mock, patch

from custom_components.hubitat.const import DOMAIN
from custom_components.hubitat.hub import _remove_unshared_devices


def test_remove_unshared_devices() -> None:
    current = Mock(id="current")
    hub = Mock(
        id="hub",
        devices={"current": current},
        config_entry=Mock(entry_id="entry"),
    )
    current_device = Mock(
        id="current-device", name="Current", identifiers={(DOMAIN, "hub:current")}
    )
    stale_device = Mock(
        id="stale-device", name="Stale", identifiers={(DOMAIN, "hub:stale")}
    )
    hub_device = Mock(id="hub-device", name="Hub", identifiers={(DOMAIN, "hub")})
    other_hub_device = Mock(
        id="other-device", name="Other", identifiers={(DOMAIN, "other:stale")}
    )
    registry = Mock()

    with (
        patch(
            "custom_components.hubitat.hub.device_registry.async_get",
            return_value=registry,
        ),
        patch(
            "custom_components.hubitat.hub.device_registry.async_entries_for_config_entry",
            return_value=[current_device, stale_device, hub_device, other_hub_device],
        ) as entries_for_config_entry,
    ):
        _remove_unshared_devices(hub, Mock())

    entries_for_config_entry.assert_called_once_with(registry, "entry")
    registry.async_remove_device.assert_called_once_with("stale-device")
