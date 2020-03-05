"""Support for Hubitat switches."""

from logging import getLogger
import re
from typing import Any, List, Optional

import hubitatmaker as hm
import voluptuous as vol

from homeassistant.components.switch import (
    DEVICE_CLASS_OUTLET,
    DEVICE_CLASS_SWITCH,
    SwitchDevice,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, ICON_ALARM, SERVICE_ALARM_SIREN_ON, SERVICE_ALARM_STROBE_ON
from .device import HubitatEntity, HubitatEventEmitter, get_hub
from .fan import is_fan
from .light import is_light

_LOGGER = getLogger(__name__)

_NAME_TEST = re.compile(r"\bswitch\b", re.IGNORECASE)

ENTITY_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_id})


class HubitatSwitch(HubitatEntity, SwitchDevice):
    """Representation of a Hubitat switch."""

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self.get_str_attr("switch") == "on"

    @property
    def device_class(self) -> str:
        """Return the class of this device, from component DEVICE_CLASSES."""
        if _NAME_TEST.match(self._device.name):
            return DEVICE_CLASS_SWITCH
        return DEVICE_CLASS_OUTLET

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        _LOGGER.debug(f"Turning on {self.name} with {kwargs}")
        await self.send_command(hm.CMD_ON)

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
        _LOGGER.debug(f"Activating alarm %s", self.name)
        await self.send_command(hm.CMD_BOTH)

    async def siren_on(self) -> None:
        """Turn on the siren."""
        _LOGGER.debug(f"Turning on siren for %s", self.name)
        await self.send_command(hm.CMD_SIREN)

    async def strobe_on(self) -> None:
        """Turn on the strobe."""
        _LOGGER.debug(f"Turning on strobe for %s", self.name)
        await self.send_command(hm.CMD_STROBE)


def is_switch(device: hm.Device) -> bool:
    """Return True if device looks like a switch."""
    return (
        hm.CAP_SWITCH in device.capabilities
        and not is_light(device)
        and not is_fan(device)
    )


def is_energy_meter(device: hm.Device) -> bool:
    """Return True if device can measure power."""
    return hm.CAP_POWER_METER in device.capabilities


def is_alarm(device: hm.Device) -> bool:
    """Return True if the device is an alarm."""
    return hm.CAP_ALARM in device.capabilities


def is_button_controller(device: hm.Device) -> bool:
    """Return true if the device is a stateless button controller."""
    return (
        hm.CAP_PUSHABLE_BUTTON in device.capabilities
        or hm.CAP_HOLDABLE_BUTTON in device.capabilities
        or hm.CAP_DOUBLE_TAPABLE_BUTTON in device.capabilities
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities,
) -> None:
    """Initialize switch devices."""
    hub = get_hub(hass, entry.entry_id)
    devices = hub.devices
    switch_devs = [devices[i] for i in devices if is_switch(devices[i])]
    switches: List[HubitatSwitch] = []
    for s in switch_devs:
        if is_energy_meter(s):
            switches.append(HubitatPowerMeterSwitch(hub=hub, device=s))
        else:
            switches.append(HubitatSwitch(hub=hub, device=s))
    async_add_entities(switches)
    hub.add_entities(switches)
    _LOGGER.debug("Added entities for switches: %s", switches)

    button_controllers = [
        HubitatEventEmitter(hub=hub, device=devices[i])
        for i in devices
        if is_button_controller(devices[i])
    ]
    for bc in button_controllers:
        hass.async_create_task(bc.update_device_registry())
    hub.add_event_emitters(button_controllers)
    _LOGGER.debug("Added entities for pushbutton controllers: %s", button_controllers)

    alarms = [
        HubitatAlarm(hub=hub, device=devices[i])
        for i in devices
        if is_alarm(devices[i])
    ]
    async_add_entities(alarms)
    hub.add_entities(alarms)
    _LOGGER.debug("Added entities for alarms: %s", alarms)

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
