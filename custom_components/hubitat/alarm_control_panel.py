"""Support for Hubitat security keypads."""

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

from .const import HassStateAttribute
from .device import HubitatEntity
from .entities import create_and_add_entities
from .hubitatmaker.const import (
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
    DeviceState,
)
from .hubitatmaker.types import Device
from .types import EntityAdder

_LOGGER = getLogger(__name__)

_device_attrs = (
    DeviceAttribute.ALARM,
    DeviceAttribute.CODE_CHANGED,
    DeviceAttribute.CODE_LENGTH,
    DeviceAttribute.ENTRY_DELAY,
    DeviceAttribute.EXIT_DELAY,
    DeviceAttribute.LOCK_CODES,
    DeviceAttribute.MAX_CODES,
    DeviceAttribute.SECURITY_KEYPAD,
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
        return self.get_str_attr(DeviceAttribute.ALARM)

    @property
    def changed_by(self) -> Optional[str]:
        """Last change triggered by."""
        return self.get_str_attr(DeviceAttribute.CODE_CHANGED)

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
        return self.get_int_attr(DeviceAttribute.CODE_LENGTH)

    @property
    def codes(self) -> Optional[Dict[str, Dict[str, str]]]:
        return self.get_json_attr(DeviceAttribute.LOCK_CODES)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        return {
            HassStateAttribute.ALARM: self.alarm,
            HassStateAttribute.CODES: self.codes,
            HassStateAttribute.CODE_LENGTH: self.code_length,
            HassStateAttribute.ENTRY_DELAY: self.entry_delay,
            HassStateAttribute.EXIT_DELAY: self.exit_delay,
            HassStateAttribute.MAX_CODES: self.max_codes,
        }

    @property
    def entry_delay(self) -> Optional[int]:
        """Return the entry delay."""
        return self.get_int_attr(DeviceAttribute.ENTRY_DELAY)

    @property
    def exit_delay(self) -> Optional[int]:
        """Return the exit delay."""
        return self.get_int_attr(DeviceAttribute.EXIT_DELAY)

    @property
    def max_codes(self) -> Optional[int]:
        """Return the maximum number of codes the keypad supports."""
        return self.get_int_attr(DeviceAttribute.MAX_CODES)

    @property
    def state(self) -> Optional[str]:
        """Return the maximum number of codes the keypad supports."""
        state = self.get_attr(DeviceAttribute.SECURITY_KEYPAD)
        if state == DeviceState.ARMED_AWAY:
            return STATE_ALARM_ARMED_AWAY
        if state == DeviceState.ARMED_HOME:
            return STATE_ALARM_ARMED_HOME
        if state == DeviceState.ARMED_NIGHT:
            return STATE_ALARM_ARMED_NIGHT
        if state == DeviceState.DISARMED:
            return STATE_ALARM_DISARMED
        return None

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        features = SUPPORT_ALARM_ARM_AWAY | SUPPORT_ALARM_ARM_HOME
        if DeviceCommand.ARM_NIGHT in self._device.commands:
            features |= SUPPORT_ALARM_ARM_NIGHT
        if DeviceCapability.ALARM in self._device.capabilities:
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
        await self.send_command(DeviceCommand.DISARM)

    async def async_alarm_arm_away(self, code: Optional[str] = None) -> None:
        """Send arm away command."""
        _LOGGER.debug("Setting armed to 'Away' for %s", self.name)
        await self.send_command(DeviceCommand.ARM_AWAY)

    async def async_alarm_arm_home(self, code: Optional[str] = None) -> None:
        """Send arm home command."""
        _LOGGER.debug("Setting armed to 'Home' for %s", self.name)
        await self.send_command(DeviceCommand.ARM_HOME)

    async def async_alarm_trigger(self, code: Optional[str] = None) -> None:
        """Send alarm trigger command."""
        _LOGGER.debug("Triggering alarm %s", self.name)
        await self.send_command(DeviceCommand.BOTH)

    async def set_entry_delay(self, delay: int) -> None:
        """Set the entry delay in seconds."""
        _LOGGER.debug("Setting entry delay for %s to %d", self.name, delay)
        await self.send_command(DeviceCommand.SET_ENTRY_DELAY, delay)

    async def set_exit_delay(self, delay: int) -> None:
        """Set the entry delay in seconds."""
        _LOGGER.debug("Setting exit delay for %s to %d", self.name, delay)
        await self.send_command(DeviceCommand.SET_EXIT_DELAY, delay)

    async def clear_code(self, position: int) -> None:
        """Clear the user code at an index."""
        await self.send_command(DeviceCommand.DELETE_CODE, position)

    async def set_code(self, position: int, code: str, name: Optional[str]) -> None:
        """Set a user code at an index."""
        arg = f"{position},{code}"
        if name is not None:
            arg = f"{arg},{name}"
        await self.send_command(DeviceCommand.SET_CODE, arg)

    async def set_code_length(self, length: int) -> None:
        """Set the acceptable code length."""
        await self.send_command(DeviceCommand.SET_CODE_LENGTH, length)


def is_security_keypad(
    device: Device, overrides: Optional[Dict[str, str]] = None
) -> bool:
    """Return True if device looks like a security keypad."""
    return DeviceCapability.SECURITY_KEYPAD in device.capabilities


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
