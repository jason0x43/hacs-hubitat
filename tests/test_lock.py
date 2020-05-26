from hubitatmaker.const import ATTR_LOCK_CODES
from hubitatmaker.types import Attribute

from tests.async_mock import MagicMock


def test_normal_lock_codes() -> None:
    hub = MagicMock()
    device = MagicMock()
    device.attributes = {
        ATTR_LOCK_CODES: Attribute(
            {
                "name": ATTR_LOCK_CODES,
                "currentValue": '{"1":{"name":"Test","code":"1234"}}',
            }
        )
    }

    from custom_components.hubitat.lock import HubitatLock

    lock = HubitatLock(hub=hub, device=device)
    assert isinstance(lock.codes, dict)


def test_encrypted_lock_codes() -> None:
    hub = MagicMock()
    device = MagicMock()
    device.attributes = {
        ATTR_LOCK_CODES: Attribute(
            {"name": ATTR_LOCK_CODES, "currentValue": "abc1235Qbxyz"}
        )
    }

    from custom_components.hubitat.lock import HubitatLock

    lock = HubitatLock(hub=hub, device=device)

    # A lock with encrypted codes should return a string for the `codes`
    # property
    assert isinstance(lock.codes, str)
