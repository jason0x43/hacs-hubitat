"""Support for Hubitat security keypads."""

from logging import getLogger
from typing import TYPE_CHECKING, Any, Unpack, cast, override

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
)
from homeassistant.components.alarm_control_panel.const import (
    AlarmControlPanelEntityFeature,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import HassStateAttribute
from .device import HubitatEntity, HubitatEntityArgs
from .entities import create_and_add_entities
from .hubitatmaker.const import (
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
    DeviceState,
)
from .hubitatmaker.types import Device

try:
    from homeassistant.components.alarm_control_panel.const import (
        AlarmControlPanelState,  # pyright: ignore[reportAssignmentType]
    )
except Exception:
    # TODO: Remove this code by 2025.11

    from enum import StrEnum

    from homeassistant.const import (
        STATE_ALARM_ARMED_AWAY,  # pyright: ignore[reportAttributeAccessIssue,reportUnknownVariableType]
        STATE_ALARM_ARMED_HOME,  # pyright: ignore[reportAttributeAccessIssue,reportUnknownVariableType]
        STATE_ALARM_ARMED_NIGHT,  # pyright: ignore[reportAttributeAccessIssue,reportUnknownVariableType]
        STATE_ALARM_DISARMED,  # pyright: ignore[reportAttributeAccessIssue,reportUnknownVariableType]
    )

    class AlarmControlPanelState(StrEnum):
        ARMED_AWAY = cast(str, STATE_ALARM_ARMED_AWAY)
        ARMED_HOME = cast(str, STATE_ALARM_ARMED_HOME)
        ARMED_NIGHT = cast(str, STATE_ALARM_ARMED_NIGHT)
        DISARMED = cast(str, STATE_ALARM_DISARMED)


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

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a Hubitat security keypad."""
        HubitatEntity.__init__(self, **kwargs)
        AlarmControlPanelEntity.__init__(self)
        self._attr_unique_id: str | None = f"{super().unique_id}::alarm_control_panel"
        self._attr_code_arm_required: bool = False
        self._attr_extra_state_attributes: dict[str, Any] = {
            HassStateAttribute.ALARM: self.alarm,
            HassStateAttribute.CODES: self.codes,
            HassStateAttribute.CODE_LENGTH: self.code_length,
            HassStateAttribute.ENTRY_DELAY: self.entry_delay,
            HassStateAttribute.EXIT_DELAY: self.exit_delay,
            HassStateAttribute.MAX_CODES: self.max_codes,
        }

        self._attr_supported_features: AlarmControlPanelEntityFeature = (  # pyright: ignore[reportIncompatibleVariableOverride]
            AlarmControlPanelEntityFeature.ARM_AWAY
            | AlarmControlPanelEntityFeature.ARM_HOME
        )
        if DeviceCommand.ARM_NIGHT in self._device.commands:
            self._attr_supported_features |= AlarmControlPanelEntityFeature.ARM_NIGHT
        if DeviceCapability.ALARM in self._device.capabilities:
            self._attr_supported_features |= AlarmControlPanelEntityFeature.TRIGGER

        self.load_state()

    @override
    def load_state(self):
        self._attr_changed_by: str | None = self._get_changed_by()
        self._attr_code_format: CodeFormat | None = self._get_code_format()
        self._attr_alarm_state: AlarmControlPanelState | None = self._get_alarm_state()  # pyright: ignore[reportIncompatibleVariableOverride]

        # TODO: remove this code by 2025.11; state will be handled by
        # _attr_alarm_state
        # see https://github.com/home-assistant/architecture/discussions/1140
        self._attr_state: StateType = self._get_alarm_state()

    def _get_changed_by(self) -> str | None:
        """Last change triggered by."""
        return self.get_str_attr(DeviceAttribute.CODE_CHANGED)

    def _get_code_format(self) -> CodeFormat | None:
        """Regex for code format or None if no code is required."""
        code_length = self.code_length
        if code_length is not None:
            return CodeFormat.NUMBER
        return None

    def _get_alarm_state(self) -> AlarmControlPanelState | None:
        """Return the maximum number of codes the keypad supports."""
        state = self.get_attr(DeviceAttribute.SECURITY_KEYPAD)
        if state == DeviceState.ARMED_AWAY:
            return AlarmControlPanelState.ARMED_AWAY
        if state == DeviceState.ARMED_HOME:
            return AlarmControlPanelState.ARMED_HOME
        if state == DeviceState.ARMED_NIGHT:
            return AlarmControlPanelState.ARMED_NIGHT
        if state == DeviceState.DISARMED:
            return AlarmControlPanelState.DISARMED
        return None

    @property
    @override
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return _device_attrs

    @property
    def alarm(self) -> str | None:
        """Alarm status."""
        return self.get_str_attr(DeviceAttribute.ALARM)

    @property
    def code_length(self) -> int | None:
        """Return the length of codes for this keypad."""
        return self.get_int_attr(DeviceAttribute.CODE_LENGTH)

    @property
    def codes(self) -> dict[str, dict[str, str]] | None:
        return self.get_dict_attr(DeviceAttribute.LOCK_CODES)

    @property
    def entry_delay(self) -> int | None:
        """Return the entry delay."""
        return self.get_int_attr(DeviceAttribute.ENTRY_DELAY)

    @property
    def exit_delay(self) -> int | None:
        """Return the exit delay."""
        return self.get_int_attr(DeviceAttribute.EXIT_DELAY)

    @property
    def max_codes(self) -> int | None:
        """Return the maximum number of codes the keypad supports."""
        return self.get_int_attr(DeviceAttribute.MAX_CODES)

    @override
    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        _LOGGER.debug("Disarming %s", self.name)
        await self.send_command(DeviceCommand.DISARM)

    @override
    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        _LOGGER.debug("Setting armed to 'Away' for %s", self.name)
        await self.send_command(DeviceCommand.ARM_AWAY)

    @override
    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        _LOGGER.debug("Setting armed to 'Home' for %s", self.name)
        await self.send_command(DeviceCommand.ARM_HOME)

    @override
    async def async_alarm_trigger(self, code: str | None = None) -> None:
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

    async def set_code(self, position: int, code: str, name: str | None) -> None:
        """Set a user code at an index."""
        arg = f"{position},{code}"
        if name is not None:
            arg = f"{arg},{name}"
        await self.send_command(DeviceCommand.SET_CODE, arg)

    async def set_code_length(self, length: int) -> None:
        """Set the acceptable code length."""
        await self.send_command(DeviceCommand.SET_CODE_LENGTH, length)


def is_security_keypad(
    device: Device, _overrides: dict[str, str] | None = None
) -> bool:
    """Return True if device looks like a security keypad."""
    return DeviceCapability.SECURITY_KEYPAD in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize security keypad devices."""
    _ = create_and_add_entities(
        hass,
        entry,
        async_add_entities,
        "alarm_control_panel",
        HubitatSecurityKeypad,
        is_security_keypad,
    )


if TYPE_CHECKING:
    from .hub import DEVICE_TYPECHECK, HUB_TYPECHECK

    test_alarm = HubitatSecurityKeypad(hub=HUB_TYPECHECK, device=DEVICE_TYPECHECK)
