from unittest.mock import Mock, patch

from custom_components.hubitat.config_flow import _get_devices, _remove_devices


def test_get_and_remove_devices() -> None:
    matching_b = Mock()
    matching_b.configure_mock(id="b", name="Beta", config_entries={"entry"})
    matching_a = Mock()
    matching_a.configure_mock(id="a", name="Alpha", config_entries={"entry", "other"})
    unrelated = Mock()
    unrelated.configure_mock(id="c", name="Gamma", config_entries={"other"})
    registry = Mock(
        devices={
            "b": matching_b,
            "a": matching_a,
            "c": unrelated,
        }
    )

    with patch(
        "custom_components.hubitat.config_flow.device_registry.async_get",
        return_value=registry,
    ):
        assert _get_devices(Mock(), Mock(entry_id="entry")) == [matching_a, matching_b]
        _remove_devices(Mock(), ["a", "b"])

    assert registry.async_remove_device.call_count == 2
