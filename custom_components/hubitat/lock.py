from typing import Any, Dict, List, Optional, Sequence, Union

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import HassStateAttribute
from .device import HubitatEntity
from .entities import create_and_add_entities
from .hubitatmaker import (
    Device,
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
    DeviceState,
)
from .types import EntityAdder

_device_attrs = (
    DeviceAttribute.CODE_LENGTH,
    DeviceAttribute.LAST_CODE_NAME,
    DeviceAttribute.LOCK,
    DeviceAttribute.LOCK_CODES,
    DeviceAttribute.MAX_CODES,
)


class HubitatLock(HubitatEntity, LockEntity):
    """Representation of a Hubitat lock."""

    @property
    def device_attrs(self) -> Optional[Sequence[str]]:
        """Return this entity's associated attributes"""
        return _device_attrs

    @property
    def code_format(self) -> Optional[str]:
        """Regex for code format or None if no code is required."""
        code_length = self.get_attr(DeviceAttribute.CODE_LENGTH)
        if code_length is not None:
            return f"^(\\d{{{code_length}}}|)$"
        return None

    @property
    def is_locked(self) -> bool:
        """Return True if the lock is locked."""
        return self.get_attr(DeviceAttribute.LOCK) == DeviceState.LOCKED

    @property
    def code_length(self) -> Optional[int]:
        return self.get_int_attr(DeviceAttribute.CODE_LENGTH)

    @property
    def codes(self) -> Union[str, Dict[str, Dict[str, str]], None]:
        try:
            codes = self.get_json_attr(DeviceAttribute.LOCK_CODES)
            if codes:
                for id in codes:
                    del codes[id]["code"]
            return codes
        except Exception:
            return self.get_str_attr(DeviceAttribute.LOCK_CODES)

    @property
    def last_code_name(self) -> Optional[str]:
        return self.get_str_attr(DeviceAttribute.LAST_CODE_NAME)

    @property
    def max_codes(self) -> Optional[int]:
        return self.get_int_attr(DeviceAttribute.MAX_CODES)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        return {
            HassStateAttribute.CODES: self.codes,
            HassStateAttribute.CODE_LENGTH: self.code_length,
            HassStateAttribute.LAST_CODE_NAME: self.last_code_name,
            HassStateAttribute.MAX_CODES: self.max_codes,
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
        await self.send_command(DeviceCommand.LOCK)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        await self.send_command(DeviceCommand.UNLOCK)

    async def clear_code(self, position: int) -> None:
        await self.send_command(DeviceCommand.DELETE_CODE, position)

    async def set_code(self, position: int, code: str, name: Optional[str]) -> None:
        arg = f"{position},{code}"
        if name is not None:
            arg = f"{arg},{name}"
        await self.send_command(DeviceCommand.SET_CODE, arg)

    async def set_code_length(self, length: int) -> None:
        await self.send_command(DeviceCommand.SET_CODE_LENGTH, length)


def is_lock(device: Device, overrides: Optional[Dict[str, str]] = None) -> bool:
    """Return True if device looks like a fan."""
    return DeviceCapability.LOCK in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: EntityAdder,
) -> None:
    """Initialize lock devices."""
    create_and_add_entities(
        hass, entry, async_add_entities, "lock", HubitatLock, is_lock
    )
