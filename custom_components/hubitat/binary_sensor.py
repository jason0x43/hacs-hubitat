"""Hubitat binary sensor entities."""

import re
from typing import Type, Unpack

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .device import HubitatEntity, HubitatEntityArgs
from .entities import create_and_add_entities
from .hubitatmaker import Device, DeviceAttribute
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
    _attribute: DeviceAttribute

    def __init__(
        self,
        *,
        attribute: DeviceAttribute,
        active_state: str,
        device_class: BinarySensorDeviceClass | None = None,
        **kwargs: Unpack[HubitatEntityArgs],
    ):
        """Initialize a battery sensor."""
        HubitatEntity.__init__(self, device_class=device_class, **kwargs)
        BinarySensorEntity.__init__(self)

        self._attribute = attribute
        self._active_state = active_state
        self._attr_unique_id = f"{super().unique_id}::binary_sensor::{self._attribute}"

    @property
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return (self._attribute,)

    @property
    def name(self) -> str:
        """Return the display name for this binary sensor."""
        return f"{super().name} {self._attribute}".title()

    @property
    def is_on(self) -> bool:
        """Return True if this sensor is on/active."""
        return self.get_str_attr(self._attribute) == self._active_state


class HubitatAccelerationSensor(HubitatBinarySensor):
    """An acceleration sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize an acceleration sensor."""
        super().__init__(
            attribute=DeviceAttribute.ACCELERATION,
            active_state="active",
            device_class=BinarySensorDeviceClass.MOVING,
            **kwargs,
        )


class HubitatCo2Sensor(HubitatBinarySensor):
    """A carbon dioxide sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a CO2 sensor."""
        super().__init__(
            attribute=DeviceAttribute.CARBON_DIOXIDE,
            active_state="detected",
            device_class=BinarySensorDeviceClass.GAS,
            **kwargs,
        )


class HubitatCoSensor(HubitatBinarySensor):
    """A carbon monoxide sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a CO sensor."""
        super().__init__(
            attribute=DeviceAttribute.CARBON_MONOXIDE,
            active_state="detected",
            device_class=BinarySensorDeviceClass.GAS,
            **kwargs,
        )


class HubitatNaturalGasSensor(HubitatBinarySensor):
    """A natural gas sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a natural gas sensor."""
        super().__init__(
            attribute=DeviceAttribute.NATURAL_GAS,
            active_state="detected",
            device_class=BinarySensorDeviceClass.GAS,
            **kwargs,
        )


class HubitatContactSensor(HubitatBinarySensor):
    """A generic contact sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a contact sensor."""
        super().__init__(
            attribute=DeviceAttribute.CONTACT,
            active_state="open",
            device_class=_get_contact_device_class(kwargs["device"]),
            **kwargs,
        )


class HubitatMoistureSensor(HubitatBinarySensor):
    """A moisture sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a moisture sensor."""
        super().__init__(
            attribute=DeviceAttribute.WATER,
            active_state="wet",
            device_class=BinarySensorDeviceClass.MOISTURE,
            **kwargs,
        )


class HubitatMotionSensor(HubitatBinarySensor):
    """A motion sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a motion sensor."""
        super().__init__(
            attribute=DeviceAttribute.MOTION,
            active_state="active",
            device_class=BinarySensorDeviceClass.MOTION,
            **kwargs,
        )


class HubitatPresenceSensor(HubitatBinarySensor):
    """A presence sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a presence sensor."""
        super().__init__(
            attribute=DeviceAttribute.PRESENCE,
            active_state="present",
            device_class=_get_presence_device_class(kwargs["device"]),
            **kwargs,
        )


class HubitatSmokeSensor(HubitatBinarySensor):
    """A smoke sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a smoke sensor."""
        super().__init__(
            attribute=DeviceAttribute.SMOKE,
            active_state="detected",
            device_class=BinarySensorDeviceClass.SMOKE,
            **kwargs,
        )


class HubitatSoundSensor(HubitatBinarySensor):
    """A sound sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a sound sensor."""
        super().__init__(
            attribute=DeviceAttribute.SOUND,
            active_state="detected",
            device_class=BinarySensorDeviceClass.SOUND,
            **kwargs,
        )


class HubitatTamperSensor(HubitatBinarySensor):
    """A tamper sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a tamper sensor."""
        super().__init__(
            attribute=DeviceAttribute.TAMPER,
            active_state="detected",
            device_class=BinarySensorDeviceClass.TAMPER,
            **kwargs,
        )


class HubitatShockSensor(HubitatBinarySensor):
    """A shock sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a shock sensor."""
        super().__init__(
            attribute=DeviceAttribute.SHOCK,
            active_state="detected",
            device_class=BinarySensorDeviceClass.VIBRATION,
            **kwargs,
        )


class HubitatHeatSensor(HubitatBinarySensor):
    """A heatAlarm sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a heatAlarm sensor."""
        super().__init__(
            attribute=DeviceAttribute.HEAT_ALARM,
            active_state="overheat",
            device_class=BinarySensorDeviceClass.HEAT,
            **kwargs,
        )


# Presence is handled specially in async_setup_entry()
_SENSOR_ATTRS: tuple[tuple[DeviceAttribute, Type[HubitatBinarySensor]], ...] = (
    (DeviceAttribute.ACCELERATION, HubitatAccelerationSensor),
    (DeviceAttribute.CARBON_DIOXIDE, HubitatCo2Sensor),
    (DeviceAttribute.CARBON_MONOXIDE, HubitatCoSensor),
    (DeviceAttribute.CONTACT, HubitatContactSensor),
    (DeviceAttribute.HEAT_ALARM, HubitatHeatSensor),
    (DeviceAttribute.MOTION, HubitatMotionSensor),
    (DeviceAttribute.NATURAL_GAS, HubitatNaturalGasSensor),
    (DeviceAttribute.PRESENCE, HubitatPresenceSensor),
    (DeviceAttribute.SHOCK, HubitatShockSensor),
    (DeviceAttribute.SMOKE, HubitatSmokeSensor),
    (DeviceAttribute.SOUND, HubitatSoundSensor),
    (DeviceAttribute.TAMPER, HubitatTamperSensor),
    (DeviceAttribute.WATER, HubitatMoistureSensor),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: EntityAdder,
) -> None:
    """Initialize binary sensor entities."""

    for attr in _SENSOR_ATTRS:

        def is_sensor(device: Device, overrides: dict[str, str] | None = None) -> bool:
            return attr[0] in device.attributes

        create_and_add_entities(
            hass, config_entry, async_add_entities, "binary_sensor", attr[1], is_sensor
        )


def _get_contact_device_class(device: Device) -> BinarySensorDeviceClass:
    """Guess the type of contact sensor from the device's label."""
    label = device.label

    for matcher in _CONTACT_MATCHERS:
        if matcher[0].search(label):
            return matcher[1]

    return BinarySensorDeviceClass.DOOR


def _get_presence_device_class(device: Device) -> BinarySensorDeviceClass:
    """Guess the type of presence sensor from the device's label."""
    label = device.label

    for matcher in _PRESENCE_MATCHERS:
        if matcher[0].search(label):
            return matcher[1]

    return BinarySensorDeviceClass.CONNECTIVITY
