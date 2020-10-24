from asyncio import Future
from typing import Awaitable

import pytest

from tests.async_mock import patch


@patch("custom_components.hubitat.config_flow.HubitatHub")
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
        await config_flow.validate_input({})
    with pytest.raises(KeyError):
        await config_flow.validate_input({"host": "host"})
    with pytest.raises(KeyError):
        await config_flow.validate_input({"host": "host", "app_id": "app_id"})
    await config_flow.validate_input(
        {"host": "host", "app_id": "app_id", "access_token": "token"}
    )
    assert check_called
