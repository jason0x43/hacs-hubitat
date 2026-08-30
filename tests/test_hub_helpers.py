from unittest.mock import Mock

import pytest

from custom_components.hubitat.hub import _get_all_devices


@pytest.mark.parametrize(
    "devices",
    [
        {"a": Mock(), "b": Mock()},
        [Mock(), Mock()],
    ],
)
def test_get_all_devices_supports_mapping_and_collection_apis(devices: object) -> None:
    registry = Mock(devices=devices)
    expected = list(devices.values()) if isinstance(devices, dict) else devices

    assert _get_all_devices(registry) == expected
