"""Hubitat binary sensor entities."""

from logging import getLogger
import re
from typing import Any, Dict

from hubitatmaker import (
    ATTR_ACCELERATION,
    ATTR_CARBON_MONOXIDE,
    ATTR_CONTACT,
    ATTR_MOTION,
    ATTR_SMOKE,
    ATTR_WATER,
    Device,
    Hub,
)

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_GARAGE_DOOR,
    DEVICE_CLASS_GAS,
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_MOVING,
    DEVICE_CLASS_SMOKE,
    DEVICE_CLASS_WINDOW,
    BinarySensorDevice,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import HubitatStatefulDevice

_LOGGER = getLogger(__name__)

_CONTACT_MATCHERS = (
    (re.compile("garage door", re.IGNORECASE), DEVICE_CLASS_GARAGE_DOOR),
    (re.compile("window", re.IGNORECASE), DEVICE_CLASS_WINDOW),
)


class HubitatBinarySensor(HubitatStatefulDevice, BinarySensorDevice):
    """A generic Hubitat sensor."""

    @property
    def is_on(self):
        """Return True if this sensor is on/active."""
        return self.get_str_attr(self._attribute) == self._active_state

    @property
    def name(self):
        """Return the display name for this sensor."""
        return f"{super().name} {self._attribute}"

    @property
    def unique_id(self):
        """Return a unique ID for this sensor."""
        return f"{super().unique_id}::{self._attribute}"

    @property
    def device_class(self):
        """Return the class of this device."""
        try:
            return self._device_class
        except AttributeError:
            return None


class HubitatAccelerationSensor(HubitatBinarySensor):
    """An acceleration sensor."""

    _active_state = "active"
    _attribute = ATTR_ACCELERATION
    _device_class = DEVICE_CLASS_MOVING


class HubitatCoSensor(HubitatBinarySensor):
    """A carbon monoxide sensor."""

    _active_state = "detected"
    _attribute = ATTR_CARBON_MONOXIDE
    _device_class = DEVICE_CLASS_GAS


class HubitatContactSensor(HubitatBinarySensor):
    """A generic contact sensor."""

    _active_state = "open"
    _attribute = ATTR_CONTACT

    def __init__(self, hub: Hub, device: Device):
        """Initialize a contact sensor."""
        super().__init__(hub=hub, device=device)
        self._device_class = _get_contact_device_class(device)


class HubitatMoistureSensor(HubitatBinarySensor):
    """A moisture sensor."""

    _active_state = "wet"
    _attribute = ATTR_WATER
    _device_class = DEVICE_CLASS_MOISTURE


class HubitatMotionSensor(HubitatBinarySensor):
    """A motion sensor."""

    _active_state = "active"
    _attribute = ATTR_MOTION
    _device_class = DEVICE_CLASS_MOTION


class HubitatSmokeSensor(HubitatBinarySensor):
    """A smoke sensor."""

    _active_state = "active"
    _attribute = ATTR_SMOKE
    _device_class = DEVICE_CLASS_SMOKE


_SENSOR_ATTRS = (
    (ATTR_ACCELERATION, HubitatAccelerationSensor),
    (ATTR_CARBON_MONOXIDE, HubitatCoSensor),
    (ATTR_CONTACT, HubitatContactSensor),
    (ATTR_MOTION, HubitatMotionSensor),
    (ATTR_SMOKE, HubitatSmokeSensor),
    (ATTR_WATER, HubitatMoistureSensor),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities,
):
    """Initialize light devices."""
    hub: Hub = hass.data[DOMAIN][entry.entry_id].hub
    devices = hub.devices
    for attr in _SENSOR_ATTRS:
        Sensor = attr[1]
        sensors = [
            Sensor(hub=hub, device=devices[i])
            for i in devices
            if attr[0] in devices[i].attributes
        ]
        async_add_entities(sensors)
        _LOGGER.debug(f"Added entities for binary sensors: {sensors}")


def _get_contact_device_class(device: Device):
    """Guess the type of contact sensor from the device's label."""
    name = device.name

    for matcher in _CONTACT_MATCHERS:
        if matcher[0].match(name):
            return matcher[1]

    return DEVICE_CLASS_DOOR
