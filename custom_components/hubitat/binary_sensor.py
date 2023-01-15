"""Hubitat binary sensor entities."""

from hubitatmaker import (
    ATTR_ACCELERATION,
    ATTR_CARBON_MONOXIDE,
    ATTR_CONTACT,
    ATTR_MOTION,
    ATTR_PRESENCE,
    ATTR_SMOKE,
    ATTR_WATER,
    Device,
)
import re
from typing import Dict, List, Optional, Sequence, Tuple, Type

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .device import Hub, HubitatEntity
from .entities import create_and_add_entities
from .types import EntityAdder

_CONTACT_MATCHERS = (
    (re.compile("garage door", re.IGNORECASE), BinarySensorDeviceClass.GARAGE_DOOR),
    (re.compile("window", re.IGNORECASE), BinarySensorDeviceClass.WINDOW),
)

_PRESENCE_MATCHERS = (
    (re.compile("presence", re.IGNORECASE), BinarySensorDeviceClass.PRESENCE),
)


class HubitatBinarySensor(HubitatEntity, BinarySensorEntity):
    """A generic Hubitat sensor."""

    _active_state: str
    _attribute: str
    _device_class: str

    @property
    def device_attrs(self) -> Optional[Sequence[str]]:
        """Return this entity's associated attributes"""
        return (self._attribute,)

    @property
    def is_on(self) -> bool:
        """Return True if this sensor is on/active."""
        return self.get_str_attr(self._attribute) == self._active_state

    @property
    def name(self) -> str:
        """Return the display name for this sensor."""
        return f"{super().name} {self._attribute}".title()

    @property
    def old_unique_ids(self) -> List[str]:
        """Return the legacy unique ID for this sensor."""
        old_parent_ids = super().old_unique_ids
        old_ids = [f"{super().unique_id}::{self._attribute}"]
        old_ids.extend([f"{id}::{self._attribute}" for id in old_parent_ids])
        return old_ids

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return f"{super().unique_id}::binary_sensor::{self._attribute}"

    @property
    def device_class(self) -> Optional[str]:
        """Return the class of this device."""
        try:
            return self._device_class
        except AttributeError:
            return None


class HubitatAccelerationSensor(HubitatBinarySensor):
    """An acceleration sensor."""

    _active_state = "active"
    _attribute = ATTR_ACCELERATION
    _device_class = BinarySensorDeviceClass.MOVING


class HubitatCoSensor(HubitatBinarySensor):
    """A carbon monoxide sensor."""

    _active_state = "detected"
    _attribute = ATTR_CARBON_MONOXIDE
    _device_class = BinarySensorDeviceClass.GAS


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
    _device_class = BinarySensorDeviceClass.MOISTURE


class HubitatMotionSensor(HubitatBinarySensor):
    """A motion sensor."""

    _active_state = "active"
    _attribute = ATTR_MOTION
    _device_class = BinarySensorDeviceClass.MOTION


class HubitatPresenceSensor(HubitatBinarySensor):
    """A presence sensor."""

    _active_state = "present"
    _attribute = ATTR_PRESENCE

    def __init__(self, hub: Hub, device: Device):
        """Initialize a presence sensor."""
        super().__init__(hub=hub, device=device)
        self._device_class = _get_presence_device_class(device)


class HubitatSmokeSensor(HubitatBinarySensor):
    """A smoke sensor."""

    _active_state = "detected"
    _attribute = ATTR_SMOKE
    _device_class = BinarySensorDeviceClass.SMOKE


# Presence is handled specially in async_setup_entry()
_SENSOR_ATTRS: Tuple[Tuple[str, Type[HubitatBinarySensor]], ...] = (
    (ATTR_ACCELERATION, HubitatAccelerationSensor),
    (ATTR_CARBON_MONOXIDE, HubitatCoSensor),
    (ATTR_CONTACT, HubitatContactSensor),
    (ATTR_MOTION, HubitatMotionSensor),
    (ATTR_PRESENCE, HubitatPresenceSensor),
    (ATTR_SMOKE, HubitatSmokeSensor),
    (ATTR_WATER, HubitatMoistureSensor),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: EntityAdder,
) -> None:
    """Initialize binary sensor entities."""

    for attr in _SENSOR_ATTRS:

        def is_sensor(
            device: Device, overrides: Optional[Dict[str, str]] = None
        ) -> bool:
            return attr[0] in device.attributes

        create_and_add_entities(
            hass, config_entry, async_add_entities, "binary_sensor", attr[1], is_sensor
        )


def _get_contact_device_class(device: Device) -> str:
    """Guess the type of contact sensor from the device's label."""
    name = device.name

    for matcher in _CONTACT_MATCHERS:
        if matcher[0].search(name):
            return matcher[1]

    return BinarySensorDeviceClass.DOOR


def _get_presence_device_class(device: Device) -> str:
    """Guess the type of presence sensor from the device's label."""
    name = device.name

    for matcher in _PRESENCE_MATCHERS:
        if matcher[0].search(name):
            return matcher[1]

    return BinarySensorDeviceClass.CONNECTIVITY
