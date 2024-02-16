from typing import Any, Unpack
from logging import getLogger
from json import loads, JSONDecodeError

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceResponse

from .const import HassStateAttribute, ATTR_POSITION
from .device import HubitatEntity, HubitatEntityArgs
from .entities import create_and_add_entities
from .hubitatmaker import (
    Device,
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
    DeviceState,
)
from .types import EntityAdder

_LOGGER = getLogger(__name__)

_device_attrs = (
    DeviceAttribute.CODE_LENGTH,
    DeviceAttribute.LAST_CODE_NAME,
    DeviceAttribute.LOCK,
    DeviceAttribute.LOCK_CODES,
    DeviceAttribute.MAX_CODES,
)


class HubitatLock(HubitatEntity, LockEntity):
    """Representation of a Hubitat lock."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a Hubitat lock."""
        HubitatEntity.__init__(self, **kwargs)
        LockEntity.__init__(self)
        self._attr_unique_id = f"{super().unique_id}::lock"

    @property
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return _device_attrs

    @property
    def code_format(self) -> str | None:
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
    def code_length(self) -> int | None:
        return self.get_int_attr(DeviceAttribute.CODE_LENGTH)

    @property
    def codes(self) -> str | dict[str, dict[str, str]] | None:
        try:
            codes = self.get_json_attr(DeviceAttribute.LOCK_CODES)
            if codes:
                for id in codes:
                    del codes[id]["code"]
            return codes
        except Exception:
            return self.get_str_attr(DeviceAttribute.LOCK_CODES)

    @property
    def last_code_name(self) -> str | None:
        return self.get_str_attr(DeviceAttribute.LAST_CODE_NAME)

    @property
    def max_codes(self) -> int | None:
        return self.get_int_attr(DeviceAttribute.MAX_CODES)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            HassStateAttribute.CODES: self.codes,
            HassStateAttribute.CODE_LENGTH: self.code_length,
            HassStateAttribute.LAST_CODE_NAME: self.last_code_name,
            HassStateAttribute.MAX_CODES: self.max_codes,
        }

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        await self.send_command(DeviceCommand.LOCK)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        await self.send_command(DeviceCommand.UNLOCK)

    async def clear_code(self, position: int) -> None:
        await self.send_command(DeviceCommand.DELETE_CODE, position)

    async def get_codes(self) -> ServiceResponse:
        codes_str = self.get_str_attr(DeviceAttribute.LOCK_CODES)
        if codes_str:
            try:
                codes = loads(codes_str)
            except JSONDecodeError:
                _LOGGER.error("json doc not decodable: %s", codes_str)
                return {HassStateAttribute.CODES: []}
            code_list = sorted([{ATTR_POSITION: key, **value} for key, value in codes.items()],
                key=lambda x: int(x[ATTR_POSITION]))
            return {HassStateAttribute.CODES: code_list}
        return {HassStateAttribute.CODES: []}

    async def set_code(self, position: int, code: str, name: str | None) -> None:
        arg = f"{position},{code}"
        if name is not None:
            arg = f"{arg},{name}"
        await self.send_command(DeviceCommand.SET_CODE, arg)

    async def set_code_length(self, length: int) -> None:
        await self.send_command(DeviceCommand.SET_CODE_LENGTH, length)


def is_lock(device: Device, overrides: dict[str, str] | None = None) -> bool:
    """Return True if device looks like a lock."""
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
