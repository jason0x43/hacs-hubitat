import hubitatmaker as hm


def test_normal_lock_codes(mocker) -> None:
    hub = mocker.MagicMock()
    device = mocker.MagicMock()
    device.attributes = {
        hm.ATTR_LOCK_CODES: hm.Attribute(
            {
                "name": hm.ATTR_LOCK_CODES,
                "currentValue": '{"1":{"name":"Test","code":"1234"}}',
            }
        )
    }

    from custom_components.hubitat.lock import HubitatLock

    lock = HubitatLock(hub=hub, device=device)
    assert isinstance(lock.codes, dict)


def test_encrypted_lock_codes(mocker) -> None:
    hub = mocker.MagicMock()
    device = mocker.MagicMock()
    device.attributes = {
        hm.ATTR_LOCK_CODES: hm.Attribute(
            {"name": hm.ATTR_LOCK_CODES, "currentValue": "abc1235Qbxyz"}
        )
    }

    from custom_components.hubitat.lock import HubitatLock

    lock = HubitatLock(hub=hub, device=device)

    # A lock with encrypted codes should return a string for the `codes`
    # property
    assert isinstance(lock.codes, str)
