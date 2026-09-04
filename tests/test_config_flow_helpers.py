from unittest.mock import Mock, patch

from custom_components.hubitat.config_flow import _get_devices, _remove_devices


def test_get_and_remove_devices() -> None:
    matching_b = Mock()
    matching_b.configure_mock(id="b", name="Beta", config_entries={"entry"})
    matching_a = Mock()
    matching_a.configure_mock(id="a", name="Alpha", config_entries={"entry", "other"})
    registry = Mock()

    with (
        patch(
            "custom_components.hubitat.config_flow.device_registry.async_get",
            return_value=registry,
        ),
        patch(
            "custom_components.hubitat.config_flow.device_registry.async_entries_for_config_entry",
            return_value=[matching_b, matching_a],
        ) as entries_for_config_entry,
    ):
        assert _get_devices(Mock(), Mock(entry_id="entry")) == [matching_a, matching_b]
        _remove_devices(Mock(), ["a", "b"])

    entries_for_config_entry.assert_called_once_with(registry, "entry")
    assert registry.async_remove_device.call_count == 2
