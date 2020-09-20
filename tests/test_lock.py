from hubitatmaker.const import ATTR_LOCK_CODES
from hubitatmaker.types import Attribute
from pytest_homeassistant_custom_component.async_mock import Mock


def test_normal_lock_codes() -> None:
    hub = Mock()
    hub.configure_mock(token="abc1235Qbxyz")

    device = Mock()
    device.configure_mock(
        attributes={
            ATTR_LOCK_CODES: Attribute(
                {
                    "name": ATTR_LOCK_CODES,
                    "currentValue": '{"1":{"name":"Test","code":"1234"}}',
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
            ATTR_LOCK_CODES: Attribute(
                {"name": ATTR_LOCK_CODES, "currentValue": "abc1235Qbxyz"}
            )
        }
    )

    from custom_components.hubitat.lock import HubitatLock

    lock = HubitatLock(hub=hub, device=device)

    # A lock with encrypted codes should return a string for the `codes`
    # property
    assert isinstance(lock.codes, str)
