from logging import getLogger
from typing import Any, Optional, cast

from hubitatmaker import (
    ATTR_CODE_LENGTH,
    ATTR_LOCK,
    ATTR_LOCK_CODES,
    CAP_LOCK,
    CMD_DELETE_CODE,
    CMD_GET_CODES,
    CMD_LOCK,
    CMD_SET_CODE,
    CMD_SET_CODE_LENGTH,
    CMD_UNLOCK,
    STATE_LOCKED,
)
import voluptuous as vol

from homeassistant.components.lock import LockDevice
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .device import HubitatEntity, get_hub

SERVICE_CLEAR_CODE = "clear_code"
SERVICE_GET_CODE = "get_code"
SERVICE_SET_CODE = "set_code"
SERVICE_SET_CODE_LENGTH = "set_code_length"

_LOGGER = getLogger(__name__)

ATTR_CODE = "code"
ATTR_LENGTH = "length"
ATTR_POSITION = "position"
ATTR_NAME = "name"

SET_CODE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): str,
        vol.Required(ATTR_POSITION): vol.Coerce(int),
        vol.Required(ATTR_CODE): str,
        vol.Optional(ATTR_NAME): str,
    }
)
GET_CODE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTITY_ID): str, vol.Required(ATTR_POSITION): vol.Coerce(int)}
)
CLEAR_CODE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTITY_ID): str, vol.Required(ATTR_POSITION): vol.Coerce(int)}
)
SET_CODE_LENGTH_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTITY_ID): str, vol.Required(ATTR_LENGTH): vol.Coerce(int)}
)


class HubitatLock(HubitatEntity, LockDevice):
    """Representation of a Hubitat lock."""

    @property
    def code_format(self) -> Optional[str]:
        """Regex for code format or None if no code is required."""
        code_length = self.get_attr(ATTR_CODE_LENGTH)
        if code_length is not None:
            return f"^\\d{code_length}$"
        return None

    @property
    def is_locked(self) -> bool:
        """Return True if the lock is locked."""
        return self.get_attr(ATTR_LOCK) == STATE_LOCKED

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        await self.send_command(CMD_LOCK)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        await self.send_command(CMD_UNLOCK)

    async def clear_code(self, position: int) -> None:
        await self.send_command(CMD_DELETE_CODE, position)

    async def get_code(self, position: int) -> None:
        await self.send_command(CMD_GET_CODES)
        codes = self.get_json_attr(ATTR_LOCK_CODES)
        if codes is None:
            return None
        code = codes.get(str(position))
        if code is None:
            return None
        return code["code"]

    async def set_code(self, position: int, code: str, name: Optional[str]) -> None:
        arg = f"{position},{code}"
        if name is not None:
            arg = f"{arg},{name}"
        await self.send_command(CMD_SET_CODE, arg)

    async def set_code_length(self, length: int) -> None:
        await self.send_command(CMD_SET_CODE_LENGTH, length)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities,
) -> None:
    """Initialize lock devices."""
    hub = get_hub(hass, entry.entry_id)
    devices = hub.devices

    locks = [
        HubitatLock(hub=hub, device=devices[i])
        for i in devices
        if CAP_LOCK in devices[i].capabilities
    ]
    async_add_entities(locks)
    hub.add_entities(locks)
    _LOGGER.debug(f"Added entities for locks: %s", locks)

    if len(locks) > 0:

        def find(entity_id: str):
            for lock in locks:
                if lock.entity_id == entity_id:
                    return lock
            return None

        async def clear_code(service: ServiceCall):
            entity_id = cast(str, service.data.get(ATTR_ENTITY_ID))
            lock = find(entity_id)
            if lock:
                pos = service.data.get(ATTR_POSITION)
                await lock.clear_code(pos)

        async def get_code(service: ServiceCall):
            entity_id = cast(str, service.data.get(ATTR_ENTITY_ID))
            lock = find(entity_id)
            if lock:
                pos = service.data.get(ATTR_POSITION)
                code = await lock.get_code(pos)
                _LOGGER.info("Usercode at slot %s is: %s", pos, code)

        async def set_code(service: ServiceCall):
            entity_id = cast(str, service.data.get(ATTR_ENTITY_ID))
            lock = find(entity_id)
            if lock:
                pos = service.data.get(ATTR_POSITION)
                code = service.data.get(ATTR_CODE)
                name = service.data.get(ATTR_NAME)
                await lock.set_code(pos, code, name)

        async def set_code_length(service: ServiceCall):
            entity_id = cast(str, service.data.get(ATTR_ENTITY_ID))
            lock = find(entity_id)
            if lock:
                length = service.data.get(ATTR_LENGTH)
                await lock.set_code_length(length)

        hass.services.async_register(
            DOMAIN, SERVICE_CLEAR_CODE, clear_code, schema=CLEAR_CODE_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_GET_CODE, get_code, schema=GET_CODE_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_SET_CODE, set_code, schema=SET_CODE_SCHEMA
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_CODE_LENGTH,
            set_code_length,
            schema=SET_CODE_LENGTH_SCHEMA,
        )
