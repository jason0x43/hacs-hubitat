from hubitatmaker.const import ATTR_LOCK_CODES
from hubitatmaker.types import Attribute


def test_normal_lock_codes(mocker) -> None:  # type: ignore
    hub = mocker.MagicMock()
    device = mocker.MagicMock()
    device.attributes = {
        ATTR_LOCK_CODES: Attribute(
            {
                "name": ATTR_LOCK_CODES,
                "currentValue": '{"1":{"name":"Test","code":"1234"}}',
            }
        )
    }

    from custom_components.hubitat.lock import HubitatLock  # type: ignore

    lock = HubitatLock(hub=hub, device=device)
    assert isinstance(lock.codes, dict)


def test_encrypted_lock_codes(mocker) -> None:  # type: ignore
    hub = mocker.MagicMock()
    device = mocker.MagicMock()
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
