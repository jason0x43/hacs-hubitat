from collections.abc import Awaitable, Callable
from typing import Any, cast
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from custom_components.hubitat.const import (
    ATTR_ARGUMENTS,
    ATTR_CODE,
    ATTR_HUB,
    ATTR_LENGTH,
    ATTR_MODE,
    ATTR_NAME,
    ATTR_POSITION,
    DOMAIN,
    HassStateAttribute,
    ServiceName,
)
from custom_components.hubitat.services import (
    async_register_services,
    async_remove_services,
)
from homeassistant.const import ATTR_COMMAND, ATTR_ENTITY_ID
from homeassistant.core import ServiceCall

ServiceHandler = Callable[[ServiceCall], Awaitable[Any]]


def registered_handlers(hass: Mock) -> dict[ServiceName, ServiceHandler]:
    return {
        service_name: cast(ServiceHandler, handler)
        for domain, service_name, handler in (
            registration.args[:3]
            for registration in hass.services.async_register.call_args_list
        )
        if domain == DOMAIN
    }


def service(data: dict[str, object]) -> ServiceCall:
    return Mock(data=data)


@pytest.mark.asyncio
async def test_entity_services() -> None:
    entity = Mock(
        entity_id="lock.front_door",
        clear_code=AsyncMock(),
        set_code=AsyncMock(),
        set_code_length=AsyncMock(),
        set_entry_delay=AsyncMock(),
        set_exit_delay=AsyncMock(),
        send_command=AsyncMock(),
    )
    hub = Mock(entities=[entity])
    hass = Mock()

    with patch(
        "custom_components.hubitat.services.get_domain_data",
        return_value={"entry": hub},
    ):
        async_register_services(hass, Mock())
        handlers = registered_handlers(hass)

        await handlers[ServiceName.CLEAR_CODE](
            service({ATTR_ENTITY_ID: entity.entity_id, ATTR_POSITION: 2})
        )
        await handlers[ServiceName.SET_CODE](
            service(
                {
                    ATTR_ENTITY_ID: entity.entity_id,
                    ATTR_POSITION: 3,
                    ATTR_CODE: "1234",
                    ATTR_NAME: "Alice",
                }
            )
        )
        await handlers[ServiceName.SET_CODE_LENGTH](
            service({ATTR_ENTITY_ID: entity.entity_id, ATTR_LENGTH: 4})
        )
        await handlers[ServiceName.SET_ENTRY_DELAY](
            service({ATTR_ENTITY_ID: entity.entity_id, ATTR_LENGTH: 10})
        )
        await handlers[ServiceName.SET_EXIT_DELAY](
            service({ATTR_ENTITY_ID: entity.entity_id, ATTR_LENGTH: 20})
        )
        await handlers[ServiceName.SEND_COMMAND](
            service(
                {
                    ATTR_ENTITY_ID: entity.entity_id,
                    ATTR_COMMAND: "setLevel",
                    ATTR_ARGUMENTS: ["50", "1"],
                }
            )
        )
        await handlers[ServiceName.SEND_COMMAND](
            service({ATTR_ENTITY_ID: entity.entity_id, ATTR_COMMAND: "refresh"})
        )

        with pytest.raises(ValueError):
            await handlers[ServiceName.CLEAR_CODE](
                service({ATTR_ENTITY_ID: "lock.missing", ATTR_POSITION: 1})
            )

    entity.clear_code.assert_awaited_once_with(2)
    entity.set_code.assert_awaited_once_with(3, "1234", "Alice")
    entity.set_code_length.assert_awaited_once_with(4)
    entity.set_entry_delay.assert_awaited_once_with(10)
    entity.set_exit_delay.assert_awaited_once_with(20)
    entity.send_command.assert_has_awaits(
        [call("setLevel", "50", "1"), call("refresh")]
    )


@pytest.mark.asyncio
async def test_get_codes_and_hub_services() -> None:
    entity = Mock(entity_id="lock.front_door")
    hub1 = Mock(id="hub1", entities=[entity], set_hsm=AsyncMock(), set_mode=AsyncMock())
    hub2 = Mock(id="hub2", entities=[], set_hsm=AsyncMock(), set_mode=AsyncMock())
    hass = Mock()

    with patch(
        "custom_components.hubitat.services.get_domain_data",
        return_value={"one": hub1, "two": hub2},
    ):
        async_register_services(hass, Mock())
        handlers = registered_handlers(hass)

        entity.get_str_attr.return_value = '{"2":{"name":"Bob"},"1":{"name":"Alice"}}'
        response = await handlers[ServiceName.GET_CODES](
            service({ATTR_ENTITY_ID: entity.entity_id})
        )
        assert response == {
            HassStateAttribute.CODES: [
                {ATTR_POSITION: "1", "name": "Alice"},
                {ATTR_POSITION: "2", "name": "Bob"},
            ]
        }

        entity.get_str_attr.return_value = "invalid"
        response = await handlers[ServiceName.GET_CODES](
            service({ATTR_ENTITY_ID: entity.entity_id})
        )
        assert response == {HassStateAttribute.CODES: []}

        await handlers[ServiceName.SET_HSM](service({ATTR_COMMAND: "armAway"}))
        await handlers[ServiceName.SET_HUB_MODE](
            service({ATTR_MODE: "Night", ATTR_HUB: "HUB1"})
        )
        with pytest.raises(ValueError):
            await handlers[ServiceName.SET_HSM](
                service({ATTR_COMMAND: "disarm", ATTR_HUB: "missing"})
            )

    hub1.set_hsm.assert_awaited_once_with("armAway")
    hub2.set_hsm.assert_awaited_once_with("armAway")
    hub1.set_mode.assert_awaited_once_with("Night")
    hub2.set_mode.assert_not_awaited()


def test_remove_services() -> None:
    hass = Mock()
    async_remove_services(hass, Mock())
    removed = {item.args[1] for item in hass.services.async_remove.call_args_list}
    assert removed == {
        ServiceName.CLEAR_CODE,
        ServiceName.SET_CODE,
        ServiceName.SET_CODE_LENGTH,
        ServiceName.SET_ENTRY_DELAY,
        ServiceName.SET_EXIT_DELAY,
        ServiceName.SEND_COMMAND,
        ServiceName.SET_HSM,
        ServiceName.SET_HUB_MODE,
    }
