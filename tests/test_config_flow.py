import pytest
import hubitatmaker


@pytest.mark.asyncio
async def test_validate_input(mocker) -> None:
    check_called = False

    async def check_config():
        nonlocal check_called
        check_called = True

    FakeHub = mocker.patch.object(hubitatmaker, "Hub")
    checker = mocker.patch.object(FakeHub.return_value, "check_config", check_config)

    from custom_components.hubitat import config_flow

    with pytest.raises(KeyError):
        await config_flow.validate_input({})
    with pytest.raises(KeyError):
        await config_flow.validate_input({"host": "host"})
    with pytest.raises(KeyError):
        await config_flow.validate_input({"host": "host", "app_id": "app_id"})
    await config_flow.validate_input(
        {"host": "host", "app_id": "app_id", "access_token": "token"}
    )
    assert check_called
