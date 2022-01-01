from asyncio import Future
import pytest
from typing import Awaitable
from unittest.mock import patch


@patch("custom_components.hubitat.config_flow.HubitatHub")
@pytest.mark.asyncio
async def test_validate_input(HubitatHub) -> None:
    check_called = False

    def check_config() -> Awaitable[None]:
        nonlocal check_called
        check_called = True
        future: Future[None] = Future()
        future.set_result(None)
        return future

    HubitatHub.return_value.check_config = check_config

    from custom_components.hubitat import config_flow

    with pytest.raises(KeyError):
        await config_flow._validate_input({})
    with pytest.raises(KeyError):
        await config_flow._validate_input({"host": "host"})
    with pytest.raises(KeyError):
        await config_flow._validate_input({"host": "host", "app_id": "app_id"})
    await config_flow._validate_input(
        {
            "host": "host",
            "app_id": "app_id",
            "access_token": "token",
            "server_port": 0,
            "server_url": None,
            "use_server_url": False,
        }
    )
    assert check_called
