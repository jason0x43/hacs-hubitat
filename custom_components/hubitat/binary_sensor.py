"""Hubitat binary sensor entities."""

import re
from dataclasses import dataclass
from typing import Pattern, Type, Unpack

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


@dataclass
class ContactInfo:
    matcher: Pattern[str]
    device_class: BinarySensorDeviceClass


_CONTACT_INFOS: list[ContactInfo] = [
    ContactInfo(
        re.compile("garage door", re.IGNORECASE),
        BinarySensorDeviceClass.GARAGE_DOOR,
    ),
    ContactInfo(
        re.compile("door", re.IGNORECASE),
        BinarySensorDeviceClass.DOOR,
    ),
    ContactInfo(re.compile("window", re.IGNORECASE), BinarySensorDeviceClass.WINDOW),
    ContactInfo(re.compile(".*"), BinarySensorDeviceClass.OPENING),
]


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
        super().__init__(
            attribute=DeviceAttribute.ACCELERATION,
            active_state="active",
            device_class=BinarySensorDeviceClass.MOVING,
            **kwargs,
        )


class HubitatCo2Sensor(HubitatBinarySensor):
    """A carbon dioxide sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.CARBON_DIOXIDE,
            active_state="detected",
            device_class=BinarySensorDeviceClass.GAS,
            **kwargs,
        )


class HubitatCoSensor(HubitatBinarySensor):
    """A carbon monoxide sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.CARBON_MONOXIDE,
            active_state="detected",
            device_class=BinarySensorDeviceClass.GAS,
            **kwargs,
        )


class HubitatContactSensor(HubitatBinarySensor):
    """A generic contact sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        info = _get_contact_info(kwargs["device"])

        super().__init__(
            attribute=DeviceAttribute.CONTACT,
            active_state="open",
            device_class=info.device_class,
            **kwargs,
        )


class HubitatMoistureSensor(HubitatBinarySensor):
    """A moisture sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.WATER,
            active_state="wet",
            device_class=BinarySensorDeviceClass.MOISTURE,
            **kwargs,
        )


class HubitatMotionSensor(HubitatBinarySensor):
    """A motion sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.MOTION,
            active_state="active",
            device_class=BinarySensorDeviceClass.MOTION,
            **kwargs,
        )


class HubitatNaturalGasSensor(HubitatBinarySensor):
    """A natural gas sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.NATURAL_GAS,
            active_state="detected",
            device_class=BinarySensorDeviceClass.GAS,
            **kwargs,
        )


class HubitatNetworkStatusSensor(HubitatBinarySensor):
    """A network status sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.NETWORK_STATUS,
            active_state="online",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            **kwargs,
        )


class HubitatPresenceSensor(HubitatBinarySensor):
    """A presence sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.PRESENCE,
            active_state="present",
            device_class=BinarySensorDeviceClass.PRESENCE,
            **kwargs,
        )


class HubitatSmokeSensor(HubitatBinarySensor):
    """A smoke sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.SMOKE,
            active_state="detected",
            device_class=BinarySensorDeviceClass.SMOKE,
            **kwargs,
        )


class HubitatSoundSensor(HubitatBinarySensor):
    """A sound sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.SOUND,
            active_state="detected",
            device_class=BinarySensorDeviceClass.SOUND,
            **kwargs,
        )


class HubitatTamperSensor(HubitatBinarySensor):
    """A tamper sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.TAMPER,
            active_state="detected",
            device_class=BinarySensorDeviceClass.TAMPER,
            **kwargs,
        )


class HubitatShockSensor(HubitatBinarySensor):
    """A shock sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.SHOCK,
            active_state="detected",
            device_class=BinarySensorDeviceClass.VIBRATION,
            **kwargs,
        )


class HubitatHeatSensor(HubitatBinarySensor):
    """A heatAlarm sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.HEAT_ALARM,
            active_state="overheat",
            device_class=BinarySensorDeviceClass.HEAT,
            **kwargs,
        )


class HubitatValveSensor(HubitatBinarySensor):
    """A valve sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.VALVE,
            active_state="open",
            device_class=BinarySensorDeviceClass.OPENING,
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
    (DeviceAttribute.NETWORK_STATUS, HubitatNetworkStatusSensor),
    (DeviceAttribute.PRESENCE, HubitatPresenceSensor),
    (DeviceAttribute.SHOCK, HubitatShockSensor),
    (DeviceAttribute.SMOKE, HubitatSmokeSensor),
    (DeviceAttribute.SOUND, HubitatSoundSensor),
    (DeviceAttribute.TAMPER, HubitatTamperSensor),
    (DeviceAttribute.VALVE, HubitatValveSensor),
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


def _get_contact_info(device: Device) -> ContactInfo:
    """Guess the type of contact sensor from the device's label."""
    label = device.label

    for info in _CONTACT_INFOS:
        if info.matcher.search(label):
            return info

    return _CONTACT_INFOS[len(_CONTACT_INFOS) - 1]
