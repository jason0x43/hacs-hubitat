from unittest.mock import Mock

import pytest

from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from custom_components.hubitat.hubitatmaker.types import Attribute


def test_normal_lock_codes() -> None:
    hub = Mock()
    hub.configure_mock(token="abc1235Qbxyz")

    device = Mock()
    device.configure_mock(
        attributes={
            DeviceAttribute.LOCK_CODES: Attribute(
                {
                    "name": DeviceAttribute.LOCK_CODES,
                    "currentValue": '{"1":{"name":"Test","code":"1234"}}',
                    "dataType": "JSON_OBJECT",
                    "unit": None,
                }
            )
        }
    )

    from custom_components.hubitat.lock import HubitatLock

    lock = HubitatLock(hub=hub, device=device)
    codes = lock.codes
    assert isinstance(codes, dict)
    assert codes["1"].get("name") == "Test"
    assert codes["1"].get("code") is None


def test_encrypted_lock_codes() -> None:
    hub = Mock()
    hub.configure_mock(token="abc1235Qbxyz")

    device = Mock()
    device.configure_mock(
        attributes={
            DeviceAttribute.LOCK_CODES: Attribute(
                {
                    "name": DeviceAttribute.LOCK_CODES,
                    "currentValue": "abc1235Qbxyz",
                    "dataType": "STRING",
                    "unit": None,
                }
            )
        }
    )

    from custom_components.hubitat.lock import HubitatLock

    lock = HubitatLock(hub=hub, device=device)

    # A lock with encrypted codes should return a string for the `codes`
    # property
    assert isinstance(lock.codes, str)


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("locked", True),
        ("unlocked", False),
        ("unlocked with timeout", False),
        ("unknown", None),
        (None, None),
    ],
)
def test_is_locked_state(state: str | None, expected: bool | None) -> None:
    hub = Mock()
    hub.configure_mock(token="abc1235Qbxyz")

    attributes = {}
    if state is not None:
        attributes[DeviceAttribute.LOCK] = Attribute(
            {
                "name": DeviceAttribute.LOCK,
                "currentValue": state,
                "dataType": "ENUM",
                "unit": None,
            }
        )

    device = Mock()
    device.configure_mock(attributes=attributes)

    from custom_components.hubitat.lock import HubitatLock

    lock = HubitatLock(hub=hub, device=device)

    # An unknown state (e.g. a lock that jammed while locking) must not be
    # reported as unlocked
    assert lock.is_locked is expected
