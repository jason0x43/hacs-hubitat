"""Support for Hubitat switches."""

from logging import getLogger
import re
from typing import Any, Optional

from hubitatmaker.const import (
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
)
from hubitatmaker.types import Device
import voluptuous as vol

from homeassistant.components.switch import DEVICE_CLASS_OUTLET, DEVICE_CLASS_SWITCH
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

try:
    from homeassistant.components.switch import SwitchEntity
except ImportError:
    from homeassistant.components.switch import SwitchDevice as SwitchEntity  # type: ignore


_LOGGER = getLogger(__name__)

_NAME_TEST = re.compile(r"\bswitch\b", re.IGNORECASE)

ENTITY_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_id})


class HubitatSwitch(HubitatEntity, SwitchEntity):
    """Representation of a Hubitat switch."""

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        _LOGGER.debug(f"Turning on {self.name} with {kwargs}")
        await self.send_command(CMD_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        _LOGGER.debug(f"Turning off {self.name}")
        await self.send_command("off")


class HubitatPowerMeterSwitch(HubitatSwitch):
    @property
    def current_power_w(self) -> Optional[float]:
        """Return the current power usage in W."""
        return self.get_float_attr("power")


class HubitatAlarm(HubitatSwitch):
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


def is_switch(device: Device) -> bool:
    """Return True if device looks like a switch."""
    return (
        CAP_SWITCH in device.capabilities
        and not is_light(device)
        and not is_fan(device)
    )


def is_energy_meter(device: Device) -> bool:
    """Return True if device can measure power."""
    return CAP_POWER_METER in device.capabilities


def is_alarm(device: Device) -> bool:
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
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: EntityAdder,
) -> None:
    """Initialize switch devices."""
    await create_and_add_entities(
        hass,
        entry,
        async_add_entities,
        "switch",
        HubitatSwitch,
        lambda dev: is_switch(dev) and not is_energy_meter(dev),
    )

    await create_and_add_entities(
        hass,
        entry,
        async_add_entities,
        "switch",
        HubitatPowerMeterSwitch,
        lambda dev: is_switch(dev) and is_energy_meter(dev),
    )

    create_and_add_event_emitters(hass, entry, is_button_controller)

    alarms = await create_and_add_entities(
        hass, entry, async_add_entities, "switch", HubitatAlarm, is_alarm
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
