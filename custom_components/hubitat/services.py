from logging import getLogger
from typing import Union, cast

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_COMMAND, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .alarm_control_panel import HubitatSecurityKeypad
from .const import (
    ATTR_ARGUMENTS,
    ATTR_CODE,
    ATTR_DELAY,
    ATTR_HUB,
    ATTR_LENGTH,
    ATTR_MODE,
    ATTR_NAME,
    ATTR_POSITION,
    DOMAIN,
    ServiceName,
)
from .device import HubitatEntity
from .hub import get_hub
from .lock import HubitatLock

_LOGGER = getLogger(__name__)

CLEAR_CODE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTITY_ID): cv.entity_id, vol.Required(ATTR_POSITION): int}
)
SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_COMMAND): str,
        vol.Optional(ATTR_ARGUMENTS): vol.Or([vol.Coerce(str)], vol.Coerce(str)),
    }
)
SET_CODE_LENGTH_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTITY_ID): cv.entity_id, vol.Required(ATTR_LENGTH): int}
)
SET_CODE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_POSITION): vol.Coerce(int),
        vol.Required(ATTR_CODE): vol.Coerce(str),
        vol.Optional(ATTR_NAME): str,
    }
)
SET_DELAY_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTITY_ID): cv.entity_id, vol.Required(ATTR_DELAY): int}
)
SET_HSM_SCHEMA = vol.Schema(
    {vol.Required(ATTR_COMMAND): str, vol.Optional(ATTR_HUB): str}
)
SET_HUB_MODE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_MODE): str, vol.Optional(ATTR_HUB): str}
)


def async_register_services(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    hub = get_hub(hass, entry.entry_id)

    def get_entity(service: ServiceCall) -> HubitatEntity:
        entity_id = cast(str, service.data.get(ATTR_ENTITY_ID))
        for entity in hub.entities:
            if entity.entity_id == entity_id:
                return cast(HubitatEntity, entity)
        raise ValueError(f"Invalid or unknown entity '{entity_id}'")

    async def clear_code(service: ServiceCall) -> None:
        entity = cast(Union[HubitatLock, HubitatSecurityKeypad], get_entity(service))
        pos = cast(int, service.data.get(ATTR_POSITION))
        await entity.clear_code(pos)

    async def send_command(service: ServiceCall) -> None:
        entity = get_entity(service)
        cmd = cast(str, service.data.get(ATTR_COMMAND))
        args = cast(str, service.data.get(ATTR_ARGUMENTS))
        if args is not None:
            if not isinstance(args, list):
                args = [args]
            await entity.send_command(cmd, *args)
        else:
            await entity.send_command(cmd)

    async def set_code(service: ServiceCall) -> None:
        entity = cast(Union[HubitatLock, HubitatSecurityKeypad], get_entity(service))
        pos = cast(int, service.data.get(ATTR_POSITION))
        code = cast(str, service.data.get(ATTR_CODE))
        name = cast(str, service.data.get(ATTR_NAME))
        await entity.set_code(pos, code, name)

    async def set_code_length(service: ServiceCall) -> None:
        entity = cast(Union[HubitatLock, HubitatSecurityKeypad], get_entity(service))
        length = cast(int, service.data.get(ATTR_LENGTH))
        await entity.set_code_length(length)

    async def set_entry_delay(service: ServiceCall) -> None:
        entity = cast(HubitatSecurityKeypad, get_entity(service))
        delay = cast(int, service.data.get(ATTR_LENGTH))
        await entity.set_entry_delay(delay)

    async def set_exit_delay(service: ServiceCall) -> None:
        entity = cast(HubitatSecurityKeypad, get_entity(service))
        delay = cast(int, service.data.get(ATTR_LENGTH))
        await entity.set_exit_delay(delay)

    async def set_hsm(service: ServiceCall) -> None:
        target_hub = hub
        if ATTR_HUB in service.data:
            hub_id = cast(str, service.data.get(ATTR_HUB)).lower()
            found_hub = False
            for _hub in hass.data[DOMAIN].values():
                if _hub.id == hub_id:
                    found_hub = True
                    target_hub = _hub
            if not found_hub:
                _LOGGER.error("Could not find a hub with ID %s", hub_id)
                return

        command = cast(str, service.data.get(ATTR_COMMAND))
        await target_hub.set_hsm(command)

    async def set_hub_mode(service: ServiceCall) -> None:
        target_hub = hub
        if ATTR_HUB in service.data:
            hub_id = cast(str, service.data.get(ATTR_HUB)).lower()
            found_hub = False
            for _hub in hass.data[DOMAIN].values():
                if _hub.id == hub_id:
                    found_hub = True
                    target_hub = _hub
            if not found_hub:
                _LOGGER.error("Could not find a hub with ID %s", hub_id)
                return

        mode = cast(str, service.data.get(ATTR_MODE))
        await target_hub.set_mode(mode)

    hass.services.async_register(
        DOMAIN, ServiceName.CLEAR_CODE, clear_code, schema=CLEAR_CODE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, ServiceName.SEND_COMMAND, send_command, schema=SEND_COMMAND_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, ServiceName.SET_CODE, set_code, schema=SET_CODE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        ServiceName.SET_CODE_LENGTH,
        set_code_length,
        schema=SET_CODE_LENGTH_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, ServiceName.SET_ENTRY_DELAY, set_entry_delay, schema=SET_DELAY_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, ServiceName.SET_EXIT_DELAY, set_exit_delay, schema=SET_DELAY_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, ServiceName.SET_HSM, set_hsm, schema=SET_HSM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, ServiceName.SET_HUB_MODE, set_hub_mode, schema=SET_HUB_MODE_SCHEMA
    )


def async_remove_services(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    hass.services.async_remove(DOMAIN, ServiceName.CLEAR_CODE)
    hass.services.async_remove(DOMAIN, ServiceName.SET_CODE)
    hass.services.async_remove(DOMAIN, ServiceName.SET_CODE_LENGTH)
    hass.services.async_remove(DOMAIN, ServiceName.SET_ENTRY_DELAY)
    hass.services.async_remove(DOMAIN, ServiceName.SET_EXIT_DELAY)
    hass.services.async_remove(DOMAIN, ServiceName.SEND_COMMAND)
    hass.services.async_remove(DOMAIN, ServiceName.SET_HSM)
    hass.services.async_remove(DOMAIN, ServiceName.SET_HUB_MODE)
