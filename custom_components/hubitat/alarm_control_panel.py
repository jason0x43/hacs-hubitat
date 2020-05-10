"""Support for Hubitat security keypads."""

from logging import getLogger
from typing import Any, Dict, Optional

import hubitatmaker as hm
import voluptuous as vol

from homeassistant.components.alarm_control_panel import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
    SUPPORT_ALARM_ARM_NIGHT,
    SUPPORT_ALARM_TRIGGER,
    AlarmControlPanel,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ALARM,
    ATTR_CODE,
    ATTR_CODE_LENGTH,
    ATTR_CODES,
    ATTR_DELAY,
    ATTR_ENTRY_DELAY,
    ATTR_EXIT_DELAY,
    ATTR_LENGTH,
    ATTR_MAX_CODES,
    ATTR_NAME,
    ATTR_POSITION,
    DOMAIN,
    SERVICE_CLEAR_CODE,
    SERVICE_SET_CODE,
    SERVICE_SET_CODE_LENGTH,
    SERVICE_SET_ENTRY_DELAY,
    SERVICE_SET_EXIT_DELAY,
)
from .device import HubitatEntity
from .entities import create_and_add_entities
from .types import EntityAdder

_LOGGER = getLogger(__name__)

CLEAR_CODE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTITY_ID): cv.entity_id, vol.Required(ATTR_POSITION): int}
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


class HubitatSecurityKeypad(HubitatEntity, AlarmControlPanel):
    """Representation of a Hubitat security keypad."""

    @property
    def alarm(self) -> Optional[str]:
        """Alarm status."""
        return self.get_attr(hm.ATTR_ALARM)

    @property
    def changed_by(self) -> Optional[str]:
        """Last change triggered by."""
        return self.get_attr(hm.ATTR_CODE_CHANGED)

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
        return self.get_int_attr(hm.ATTR_CODE_LENGTH)

    @property
    def codes(self) -> Optional[Dict[str, Dict[str, str]]]:
        return self.get_json_attr(hm.ATTR_LOCK_CODES)

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
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
        return self.get_int_attr(hm.ATTR_ENTRY_DELAY)

    @property
    def exit_delay(self) -> Optional[int]:
        """Return the exit delay."""
        return self.get_int_attr(hm.ATTR_EXIT_DELAY)

    @property
    def max_codes(self) -> Optional[int]:
        """Return the maximum number of codes the keypad supports."""
        return self.get_int_attr(hm.ATTR_MAX_CODES)

    @property
    def state(self) -> Optional[str]:
        """Return the maximum number of codes the keypad supports."""
        state = self.get_attr(hm.ATTR_SECURITY_KEYPAD)
        if state == hm.STATE_ARMED_AWAY:
            return STATE_ALARM_ARMED_AWAY
        if state == hm.STATE_ARMED_HOME:
            return STATE_ALARM_ARMED_HOME
        if state == hm.STATE_ARMED_NIGHT:
            return STATE_ALARM_ARMED_NIGHT
        if state == hm.STATE_DISARMED:
            return STATE_ALARM_DISARMED
        return None

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        features = SUPPORT_ALARM_ARM_AWAY | SUPPORT_ALARM_ARM_HOME
        if hm.CMD_ARM_NIGHT in self._device.commands:
            features |= SUPPORT_ALARM_ARM_NIGHT
        if hm.CAP_ALARM in self._device.capabilities:
            features |= SUPPORT_ALARM_TRIGGER
        return features

    async def async_alarm_disarm(self, code: Optional[str] = None) -> None:
        """Send disarm command."""
        _LOGGER.debug("Disarming %s", self.name)
        await self.send_command(hm.CMD_DISARM)

    async def async_alarm_arm_away(self, code: Optional[str] = None) -> None:
        """Send arm away command."""
        _LOGGER.debug("Setting armed to 'Away' for %s", self.name)
        await self.send_command(hm.CMD_ARM_AWAY)

    async def async_alarm_arm_home(self, code: Optional[str] = None) -> None:
        """Send arm home command."""
        _LOGGER.debug("Setting armed to 'Home' for %s", self.name)
        await self.send_command(hm.CMD_ARM_HOME)

    async def async_alarm_trigger(self, code: Optional[str] = None):
        """Send alarm trigger command."""
        _LOGGER.debug("Triggering alarm %s", self.name)
        await self.send_command(hm.CMD_BOTH)

    async def set_entry_delay(self, delay: int) -> None:
        """Set the entry delay in seconds."""
        _LOGGER.debug("Setting entry delay for %s to %d", self.name, delay)
        await self.send_command(hm.CMD_SET_ENTRY_DELAY, delay)

    async def set_exit_delay(self, delay: int) -> None:
        """Set the entry delay in seconds."""
        _LOGGER.debug("Setting exit delay for %s to %d", self.name, delay)
        await self.send_command(hm.CMD_SET_EXIT_DELAY, delay)


def is_security_keypad(device: hm.Device) -> bool:
    """Return True if device looks like a security keypad."""
    return hm.CAP_SECURITY_KEYPAD in device.capabilities


def is_alarm(device: hm.Device) -> bool:
    """Return True if device looks like an alarm."""
    return hm.CAP_ALARM in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: EntityAdder,
) -> None:
    """Initialize security keypad devices."""
    keypads = await create_and_add_entities(
        hass,
        entry,
        async_add_entities,
        "alarm_control_panel",
        HubitatSecurityKeypad,
        is_security_keypad,
    )

    if len(keypads) > 0:

        def get_entity(service: ServiceCall):
            entity_id = service.data.get(ATTR_ENTITY_ID)
            for keypad in keypads:
                if keypad.entity_id == entity_id:
                    return keypad
            return None

        async def clear_code(service: ServiceCall) -> None:
            keypad = get_entity(service)
            pos = service.data.get(ATTR_POSITION)
            await keypad.clear_code(pos)

        async def set_code(service: ServiceCall) -> None:
            keypad = get_entity(service)
            pos = service.data.get(ATTR_POSITION)
            code = service.data.get(ATTR_CODE)
            name = service.data.get(ATTR_NAME)
            await keypad.set_code(pos, code, name)

        async def set_code_length(service: ServiceCall) -> None:
            keypad = get_entity(service)
            length = service.data.get(ATTR_LENGTH)
            await keypad.set_code_length(length)

        async def set_entry_delay(service: ServiceCall) -> None:
            keypad = get_entity(service)
            length = service.data.get(ATTR_LENGTH)
            await keypad.set_entry_delay(length)

        async def set_exit_delay(service: ServiceCall) -> None:
            keypad = get_entity(service)
            length = service.data.get(ATTR_LENGTH)
            await keypad.set_exit_delay(length)

        hass.services.async_register(
            DOMAIN, SERVICE_CLEAR_CODE, clear_code, schema=CLEAR_CODE_SCHEMA
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
        hass.services.async_register(
            DOMAIN, SERVICE_SET_ENTRY_DELAY, set_entry_delay, schema=SET_DELAY_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_SET_EXIT_DELAY, set_exit_delay, schema=SET_DELAY_SCHEMA
        )
