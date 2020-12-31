"""Support for Hubitat switches."""

from logging import getLogger
import re
from typing import Any, Dict, List, Optional

from hubitatmaker import (
    CAP_ALARM,
    CAP_DOUBLE_TAPABLE_BUTTON,
    CAP_HOLDABLE_BUTTON,
    CAP_POWER_METER,
    CAP_PUSHABLE_BUTTON,
    CAP_SWITCH,
    CMD_BOTH,
    CMD_ON,
    CMD_SIREN,
    CMD_STROBE,
    Device,
)
import voluptuous as vol

from homeassistant.components.switch import (
    DEVICE_CLASS_OUTLET,
    DEVICE_CLASS_SWITCH,
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, ICON_ALARM, SERVICE_ALARM_SIREN_ON, SERVICE_ALARM_STROBE_ON
from .device import HubitatEntity
from .entities import create_and_add_entities, create_and_add_event_emitters
from .fan import is_fan
from .light import is_light
from .types import EntityAdder

_LOGGER = getLogger(__name__)

_NAME_TEST = re.compile(r"\bswitch\b", re.IGNORECASE)

ENTITY_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_id})


class HubitatSwitch(HubitatEntity, SwitchEntity):
    """Representation of a Hubitat switch."""

    _attribute: str

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self.get_str_attr("switch") == "on"

    @property
    def device_class(self) -> Optional[str]:
        """Return the class of this device, from component DEVICE_CLASSES."""
        if _NAME_TEST.match(self._device.name):
            return DEVICE_CLASS_SWITCH
        return DEVICE_CLASS_OUTLET

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this switch."""
        id = f"{super().unique_id}::switch"
        if hasattr(self, "_attribute"):
            id += f"::{self._attribute}"
        return id

    @property
    def old_unique_ids(self) -> List[str]:
        """Return the legacy unique ID for this switch."""
        old_ids = [super().unique_id]
        old_parent_ids = super().old_unique_ids
        old_ids.extend(old_parent_ids)
        return old_ids

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        _LOGGER.debug(f"Turning on {self.name} with {kwargs}")
        await self.send_command(CMD_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        _LOGGER.debug(f"Turning off {self.name}")
        await self.send_command("off")


class HubitatPowerMeterSwitch(HubitatSwitch):
    _attribute = "power_meter"

    @property
    def current_power_w(self) -> Optional[float]:
        """Return the current power usage in W."""
        return self.get_float_attr("power")


class HubitatAlarm(HubitatSwitch):
    _attribute = "alarm"

    @property
    def icon(self) -> str:
        """Return the icon."""
        return ICON_ALARM

    @property
    def name(self) -> str:
        """Return this alarm's display name."""
        return f"{super().name} alarm"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the alarm."""
        _LOGGER.debug("Activating alarm %s", self.name)
        await self.send_command(CMD_BOTH)

    async def siren_on(self) -> None:
        """Turn on the siren."""
        _LOGGER.debug("Turning on siren for %s", self.name)
        await self.send_command(CMD_SIREN)

    async def strobe_on(self) -> None:
        """Turn on the strobe."""
        _LOGGER.debug("Turning on strobe for %s", self.name)
        await self.send_command(CMD_STROBE)


def is_switch(device: Device, overrides: Optional[Dict[str, str]] = None) -> bool:
    """Return True if device looks like a switch."""
    if overrides and device.id in overrides and overrides[device.id] != "switch":
        return False

    return (
        CAP_SWITCH in device.capabilities
        and not is_light(device, overrides)
        and not is_fan(device, overrides)
    )


def is_energy_meter(device: Device, overrides: Optional[Dict[str, str]] = None) -> bool:
    """Return True if device can measure power."""
    return CAP_POWER_METER in device.capabilities


def is_alarm(device: Device, overrides: Optional[Dict[str, str]] = None) -> bool:
    """Return True if the device is an alarm."""
    return CAP_ALARM in device.capabilities


def is_button_controller(device: Device) -> bool:
    """Return true if the device is a stateless button controller."""
    return (
        CAP_PUSHABLE_BUTTON in device.capabilities
        or CAP_HOLDABLE_BUTTON in device.capabilities
        or CAP_DOUBLE_TAPABLE_BUTTON in device.capabilities
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: EntityAdder,
) -> None:
    """Initialize switch devices."""

    def _is_simple_switch(
        device: Device, overrides: Optional[Dict[str, str]] = None
    ) -> bool:
        return is_switch(device, overrides) and not is_energy_meter(device, overrides)

    await create_and_add_entities(
        hass,
        config_entry,
        async_add_entities,
        "switch",
        HubitatSwitch,
        _is_simple_switch,
    )

    def _is_smart_switch(
        device: Device, overrides: Optional[Dict[str, str]] = None
    ) -> bool:
        return is_switch(device, overrides) and is_energy_meter(device, overrides)

    await create_and_add_entities(
        hass,
        config_entry,
        async_add_entities,
        "switch",
        HubitatPowerMeterSwitch,
        _is_smart_switch,
    )

    await create_and_add_event_emitters(hass, config_entry, is_button_controller)

    alarms = await create_and_add_entities(
        hass, config_entry, async_add_entities, "switch", HubitatAlarm, is_alarm
    )

    if len(alarms) > 0:

        def get_entity(service: ServiceCall) -> Optional[HubitatAlarm]:
            entity_id = service.data.get(ATTR_ENTITY_ID)
            for alarm in alarms:
                if alarm.entity_id == entity_id:
                    return alarm
            _LOGGER.warning("No alarm for ID %s", entity_id)
            return None

        async def siren_on(service: ServiceCall) -> None:
            alarm = get_entity(service)
            if alarm:
                await alarm.siren_on()

        async def strobe_on(service: ServiceCall) -> None:
            alarm = get_entity(service)
            if alarm is not None:
                await alarm.strobe_on()

        hass.services.async_register(
            DOMAIN, SERVICE_ALARM_SIREN_ON, siren_on, schema=ENTITY_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_ALARM_STROBE_ON, strobe_on, schema=ENTITY_SCHEMA
        )
