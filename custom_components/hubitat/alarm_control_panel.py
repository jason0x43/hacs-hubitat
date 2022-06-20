"""Support for Hubitat security keypads."""

from hubitatmaker.const import (
    ATTR_ALARM as HE_ATTR_ALARM,
    ATTR_CODE_CHANGED as HE_ATTR_CODE_CHANGED,
    ATTR_CODE_LENGTH as HE_ATTR_CODE_LENGTH,
    ATTR_ENTRY_DELAY as HE_ATTR_ENTRY_DELAY,
    ATTR_EXIT_DELAY as HE_ATTR_EXIT_DELAY,
    ATTR_LOCK_CODES as HE_ATTR_LOCK_CODES,
    ATTR_MAX_CODES as HE_ATTR_MAX_CODES,
    ATTR_SECURITY_KEYPAD as HE_ATTR_SECURITY_KEYPAD,
    CAP_ALARM,
    CAP_SECURITY_KEYPAD,
    CMD_ARM_AWAY,
    CMD_ARM_HOME,
    CMD_ARM_NIGHT,
    CMD_BOTH,
    CMD_DELETE_CODE,
    CMD_DISARM,
    CMD_SET_CODE,
    CMD_SET_CODE_LENGTH,
    CMD_SET_ENTRY_DELAY,
    CMD_SET_EXIT_DELAY,
    STATE_ARMED_AWAY,
    STATE_ARMED_HOME,
    STATE_ARMED_NIGHT,
    STATE_DISARMED,
)
from hubitatmaker.types import Device
from logging import getLogger
from typing import Any, Dict, List, Optional, Sequence

from homeassistant.components.alarm_control_panel import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
    SUPPORT_ALARM_ARM_NIGHT,
    SUPPORT_ALARM_TRIGGER,
    AlarmControlPanelEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
)
from homeassistant.core import HomeAssistant

from .const import (
    ATTR_ALARM,
    ATTR_CODE_LENGTH,
    ATTR_CODES,
    ATTR_ENTRY_DELAY,
    ATTR_EXIT_DELAY,
    ATTR_MAX_CODES,
)
from .device import HubitatEntity
from .entities import create_and_add_entities
from .types import EntityAdder

_LOGGER = getLogger(__name__)

_device_attrs = (
    HE_ATTR_ALARM,
    HE_ATTR_CODE_CHANGED,
    HE_ATTR_CODE_LENGTH,
    HE_ATTR_ENTRY_DELAY,
    HE_ATTR_EXIT_DELAY,
    HE_ATTR_LOCK_CODES,
    HE_ATTR_MAX_CODES,
    HE_ATTR_SECURITY_KEYPAD,
)


class HubitatSecurityKeypad(HubitatEntity, AlarmControlPanelEntity):
    """Representation of a Hubitat security keypad."""

    @property
    def device_attrs(self) -> Optional[Sequence[str]]:
        """Return this entity's associated attributes"""
        return _device_attrs

    @property
    def alarm(self) -> Optional[str]:
        """Alarm status."""
        return self.get_str_attr(HE_ATTR_ALARM)

    @property
    def changed_by(self) -> Optional[str]:
        """Last change triggered by."""
        return self.get_str_attr(HE_ATTR_CODE_CHANGED)

    @property
    def code_arm_required(self) -> bool:
        """Whether the code is required for arm actions."""
        return False

    @property
    def code_format(self) -> Optional[str]:
        """Regex for code format or None if no code is required."""
        code_length = self.code_length
        if code_length is not None:
            return f"^\\d{code_length}$"
        return None

    @property
    def code_length(self) -> Optional[int]:
        """Return the length of codes for this keypad."""
        return self.get_int_attr(HE_ATTR_CODE_LENGTH)

    @property
    def codes(self) -> Optional[Dict[str, Dict[str, str]]]:
        return self.get_json_attr(HE_ATTR_LOCK_CODES)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        return {
            ATTR_ALARM: self.alarm,
            ATTR_CODES: self.codes,
            ATTR_CODE_LENGTH: self.code_length,
            ATTR_ENTRY_DELAY: self.entry_delay,
            ATTR_EXIT_DELAY: self.exit_delay,
            ATTR_MAX_CODES: self.max_codes,
        }

    @property
    def entry_delay(self) -> Optional[int]:
        """Return the entry delay."""
        return self.get_int_attr(HE_ATTR_ENTRY_DELAY)

    @property
    def exit_delay(self) -> Optional[int]:
        """Return the exit delay."""
        return self.get_int_attr(HE_ATTR_EXIT_DELAY)

    @property
    def max_codes(self) -> Optional[int]:
        """Return the maximum number of codes the keypad supports."""
        return self.get_int_attr(HE_ATTR_MAX_CODES)

    @property
    def state(self) -> Optional[str]:
        """Return the maximum number of codes the keypad supports."""
        state = self.get_attr(HE_ATTR_SECURITY_KEYPAD)
        if state == STATE_ARMED_AWAY:
            return STATE_ALARM_ARMED_AWAY
        if state == STATE_ARMED_HOME:
            return STATE_ALARM_ARMED_HOME
        if state == STATE_ARMED_NIGHT:
            return STATE_ALARM_ARMED_NIGHT
        if state == STATE_DISARMED:
            return STATE_ALARM_DISARMED
        return None

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        features = SUPPORT_ALARM_ARM_AWAY | SUPPORT_ALARM_ARM_HOME
        if CMD_ARM_NIGHT in self._device.commands:
            features |= SUPPORT_ALARM_ARM_NIGHT
        if CAP_ALARM in self._device.capabilities:
            features |= SUPPORT_ALARM_TRIGGER
        return features

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this cover."""
        return f"{super().unique_id}::alarm_control_panel"

    @property
    def old_unique_ids(self) -> List[str]:
        """Return the legacy unique ID for this cover."""
        old_ids = [super().unique_id]
        old_parent_ids = super().old_unique_ids
        old_ids.extend(old_parent_ids)
        return old_ids

    async def async_alarm_disarm(self, code: Optional[str] = None) -> None:
        """Send disarm command."""
        _LOGGER.debug("Disarming %s", self.name)
        await self.send_command(CMD_DISARM)

    async def async_alarm_arm_away(self, code: Optional[str] = None) -> None:
        """Send arm away command."""
        _LOGGER.debug("Setting armed to 'Away' for %s", self.name)
        await self.send_command(CMD_ARM_AWAY)

    async def async_alarm_arm_home(self, code: Optional[str] = None) -> None:
        """Send arm home command."""
        _LOGGER.debug("Setting armed to 'Home' for %s", self.name)
        await self.send_command(CMD_ARM_HOME)

    async def async_alarm_trigger(self, code: Optional[str] = None) -> None:
        """Send alarm trigger command."""
        _LOGGER.debug("Triggering alarm %s", self.name)
        await self.send_command(CMD_BOTH)

    async def set_entry_delay(self, delay: int) -> None:
        """Set the entry delay in seconds."""
        _LOGGER.debug("Setting entry delay for %s to %d", self.name, delay)
        await self.send_command(CMD_SET_ENTRY_DELAY, delay)

    async def set_exit_delay(self, delay: int) -> None:
        """Set the entry delay in seconds."""
        _LOGGER.debug("Setting exit delay for %s to %d", self.name, delay)
        await self.send_command(CMD_SET_EXIT_DELAY, delay)

    async def clear_code(self, position: int) -> None:
        """Clear the user code at an index."""
        await self.send_command(CMD_DELETE_CODE, position)

    async def set_code(self, position: int, code: str, name: Optional[str]) -> None:
        """Set a user code at an index."""
        arg = f"{position},{code}"
        if name is not None:
            arg = f"{arg},{name}"
        await self.send_command(CMD_SET_CODE, arg)

    async def set_code_length(self, length: int) -> None:
        """Set the acceptable code length."""
        await self.send_command(CMD_SET_CODE_LENGTH, length)


def is_security_keypad(
    device: Device, overrides: Optional[Dict[str, str]] = None
) -> bool:
    """Return True if device looks like a security keypad."""
    return CAP_SECURITY_KEYPAD in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: EntityAdder,
) -> None:
    """Initialize security keypad devices."""
    create_and_add_entities(
        hass,
        entry,
        async_add_entities,
        "alarm_control_panel",
        HubitatSecurityKeypad,
        is_security_keypad,
    )
