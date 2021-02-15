from typing import Any, Dict, List, Optional, Union

from hubitatmaker import (
    ATTR_CODE_LENGTH as HM_ATTR_CODE_LENGTH,
    ATTR_LAST_CODE_NAME as HM_ATTR_LAST_CODE_NAME,
    ATTR_LOCK as HM_ATTR_LOCK,
    ATTR_LOCK_CODES as HM_ATTR_LOCK_CODES,
    ATTR_MAX_CODES as HM_ATTR_MAX_CODES,
    CAP_LOCK,
    CMD_DELETE_CODE,
    CMD_LOCK,
    CMD_SET_CODE,
    CMD_SET_CODE_LENGTH,
    CMD_UNLOCK,
    STATE_LOCKED,
    Device,
)

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import ATTR_CODE_LENGTH, ATTR_CODES, ATTR_LAST_CODE_NAME, ATTR_MAX_CODES
from .device import HubitatEntity
from .entities import create_and_add_entities
from .types import EntityAdder


class HubitatLock(HubitatEntity, LockEntity):
    """Representation of a Hubitat lock."""

    @property
    def code_format(self) -> Optional[str]:
        """Regex for code format or None if no code is required."""
        code_length = self.get_attr(HM_ATTR_CODE_LENGTH)
        if code_length is not None:
            return f"^\\d{code_length}$"
        return None

    @property
    def is_locked(self) -> bool:
        """Return True if the lock is locked."""
        return self.get_attr(HM_ATTR_LOCK) == STATE_LOCKED

    @property
    def code_length(self) -> Optional[int]:
        return self.get_int_attr(HM_ATTR_CODE_LENGTH)

    @property
    def codes(self) -> Union[str, Dict[str, Dict[str, str]], None]:
        try:
            codes = self.get_json_attr(HM_ATTR_LOCK_CODES)
            if codes:
                for id in codes:
                    del codes[id]["code"]
            return codes
        except Exception:
            return self.get_str_attr(HM_ATTR_LOCK_CODES)

    @property
    def last_code_name(self) -> Optional[str]:
        return self.get_str_attr(HM_ATTR_LAST_CODE_NAME)

    @property
    def max_codes(self) -> Optional[int]:
        return self.get_int_attr(HM_ATTR_MAX_CODES)

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        return {
            ATTR_CODES: self.codes,
            ATTR_CODE_LENGTH: self.code_length,
            ATTR_LAST_CODE_NAME: self.last_code_name,
            ATTR_MAX_CODES: self.max_codes,
        }

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this lock."""
        return f"{super().unique_id}::lock"

    @property
    def old_unique_ids(self) -> List[str]:
        """Return the legacy unique ID for this lock."""
        old_ids = [super().unique_id]
        old_parent_ids = super().old_unique_ids
        old_ids.extend(old_parent_ids)
        return old_ids

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        await self.send_command(CMD_LOCK)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        await self.send_command(CMD_UNLOCK)

    async def clear_code(self, position: int) -> None:
        await self.send_command(CMD_DELETE_CODE, position)

    async def set_code(self, position: int, code: str, name: Optional[str]) -> None:
        arg = f"{position},{code}"
        if name is not None:
            arg = f"{arg},{name}"
        await self.send_command(CMD_SET_CODE, arg)

    async def set_code_length(self, length: int) -> None:
        await self.send_command(CMD_SET_CODE_LENGTH, length)


def is_lock(device: Device, overrides: Optional[Dict[str, str]] = None) -> bool:
    """Return True if device looks like a fan."""
    return CAP_LOCK in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: EntityAdder,
) -> None:
    """Initialize lock devices."""
    await create_and_add_entities(
        hass, entry, async_add_entities, "lock", HubitatLock, is_lock
    )
