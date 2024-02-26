from asyncio import Future
from collections.abc import Awaitable
from unittest.mock import patch

import pytest


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
        _ = await config_flow._validate_input({})
    with pytest.raises(KeyError):
        _ = await config_flow._validate_input({"host": "host"})
    with pytest.raises(KeyError):
        _ = await config_flow._validate_input({"host": "host", "app_id": "app_id"})
    _ = await config_flow._validate_input(
        {
            "host": "host",
            "app_id": "app_id",
            "access_token": "token",
            "server_port": 0,
            "server_url": None,
        }
    )
    assert check_called
