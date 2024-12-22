"""Support for Hubitat switches."""

import re
from enum import StrEnum
from logging import getLogger
from typing import TYPE_CHECKING, Any, Unpack, override

import voluptuous as vol

from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ICON_ALARM, ServiceName
from .device import HubitatEntity, HubitatEntityArgs
from .entities import create_and_add_entities, create_and_add_event_emitters
from .fan import is_fan
from .hubitatmaker import Device, DeviceCapability, DeviceCommand
from .light import is_light

_LOGGER = getLogger(__name__)

_NAME_TEST = re.compile(r"\bswitch\b", re.IGNORECASE)

ENTITY_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_id})


class SwitchType(StrEnum):
    SWITCH = "switch"
    POWER = "power_meter"
    ALARM = "alarm"


class HubitatSwitch(HubitatEntity, SwitchEntity):
    """Representation of a Hubitat switch."""

    def __init__(
        self,
        type: SwitchType = SwitchType.SWITCH,
        **kwargs: Unpack[HubitatEntityArgs],
    ):
        """Initialize a Hubitat switch."""
        HubitatEntity.__init__(self, **kwargs)
        SwitchEntity.__init__(self)
        self._attr_device_class: SwitchDeviceClass = (  # pyright: ignore[reportIncompatibleVariableOverride]
            SwitchDeviceClass.SWITCH
            if _NAME_TEST.search(self._device.label)
            else SwitchDeviceClass.OUTLET
        )
        self._attr_unique_id: str | None = f"{super().unique_id}::switch"
        if type != SwitchType.SWITCH:
            self._attr_unique_id += f"::{type}"

        self.load_state()

    @override
    def load_state(self):
        self._attr_is_on: bool | None = self._get_is_on()

    def _get_is_on(self) -> bool:
        """Return True if the switch is on."""
        return self.get_str_attr(DeviceAttribute.SWITCH) == "on"

    @property
    @override
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return (DeviceAttribute.SWITCH, DeviceAttribute.POWER)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:  # pyright: ignore[reportAny]
        """Turn on the switch."""
        _LOGGER.debug(f"Turning on {self.name} with {kwargs}")
        await self.send_command(DeviceCommand.ON)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:  # pyright: ignore[reportAny]
        """Turn off the switch."""
        _LOGGER.debug(f"Turning off {self.name}")
        await self.send_command("off")


class HubitatPowerMeterSwitch(HubitatSwitch):
    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a Hubitat power meter switch."""
        super().__init__(type=SwitchType.POWER, **kwargs)

    @property
    def current_power_w(self) -> float | None:
        """Return the current power usage in W."""
        return self.get_float_attr(DeviceAttribute.POWER)


class HubitatAlarm(HubitatSwitch):
    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a Hubitat alarm."""
        super().__init__(type=SwitchType.ALARM, **kwargs)
        self._attr_name: str | None = f"{super(HubitatEntity, self).name} Alarm".title()
        self._attr_icon: str | None = ICON_ALARM

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:  # pyright: ignore[reportAny]
        """Turn on the alarm."""
        _LOGGER.debug("Activating alarm %s", self.name)
        await self.send_command(DeviceCommand.BOTH)

    async def siren_on(self) -> None:
        """Turn on the siren."""
        _LOGGER.debug("Turning on siren for %s", self.name)
        await self.send_command(DeviceCommand.SIREN)

    async def strobe_on(self) -> None:
        """Turn on the strobe."""
        _LOGGER.debug("Turning on strobe for %s", self.name)
        await self.send_command(DeviceCommand.STROBE)


def is_switch(device: Device, overrides: dict[str, str] | None = None) -> bool:
    """Return True if device looks like a switch."""
    if overrides and overrides.get(device.id) is not None:
        return overrides[device.id] == "switch"

    return (
        DeviceCapability.SWITCH in device.capabilities
        and not is_light(device, overrides)
        and not is_fan(device, overrides)
    )


def is_energy_meter(device: Device, _overrides: dict[str, str] | None = None) -> bool:
    """Return True if device can measure power."""
    return DeviceCapability.POWER_METER in device.capabilities


def is_alarm(device: Device, _overrides: dict[str, str] | None = None) -> bool:
    """Return True if the device is an alarm."""
    return DeviceCapability.ALARM in device.capabilities


def is_button_controller(device: Device) -> bool:
    """Return true if the device is a stateless button controller."""
    return (
        DeviceCapability.PUSHABLE_BUTTON in device.capabilities
        or DeviceCapability.HOLDABLE_BUTTON in device.capabilities
        or DeviceCapability.DOUBLE_TAPABLE_BUTTON in device.capabilities
        or DeviceCapability.RELEASABLE_BUTTON in device.capabilities
    )


def is_simple_switch(device: Device, overrides: dict[str, str] | None = None) -> bool:
    return is_switch(device, overrides) and not is_energy_meter(device, overrides)


def is_smart_switch(device: Device, overrides: dict[str, str] | None = None) -> bool:
    return is_switch(device, overrides) and is_energy_meter(device, overrides)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize switch devices."""

    _ = create_and_add_entities(
        hass,
        config_entry,
        async_add_entities,
        "switch",
        HubitatSwitch,
        is_simple_switch,
    )

    _ = create_and_add_entities(
        hass,
        config_entry,
        async_add_entities,
        "switch",
        HubitatPowerMeterSwitch,
        is_smart_switch,
    )

    _ = create_and_add_event_emitters(hass, config_entry, is_button_controller)

    alarms = create_and_add_entities(
        hass, config_entry, async_add_entities, "switch", HubitatAlarm, is_alarm
    )

    if len(alarms) > 0:

        def get_entity(service: ServiceCall) -> HubitatAlarm | None:
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
            DOMAIN, ServiceName.ALARM_SIREN_ON, siren_on, schema=ENTITY_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, ServiceName.ALARM_STROBE_ON, strobe_on, schema=ENTITY_SCHEMA
        )


if TYPE_CHECKING:
    from .hub import DEVICE_TYPECHECK, HUB_TYPECHECK

    test_alarm = HubitatSwitch(
        hub=HUB_TYPECHECK,
        device=DEVICE_TYPECHECK,
    )
