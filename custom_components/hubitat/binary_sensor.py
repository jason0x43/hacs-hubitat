"""Hubitat binary sensor entities."""

import re
from dataclasses import dataclass
from re import Pattern
from typing import TYPE_CHECKING, Any, Callable, Unpack, override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_HIDDEN, CONF_HOST, CONF_ID, CONF_TEMPERATURE_UNIT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device import HubitatEntity, HubitatEntityArgs
from .entities import create_and_add_entities
from .hub import get_hub
from .hubitatmaker import Device, DeviceAttribute


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


class HubitatBinarySensor(BinarySensorEntity, HubitatEntity):
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
        HubitatEntity.__init__(self, **kwargs)
        BinarySensorEntity.__init__(self)
        self._attr_device_class = device_class
        self._attribute = attribute
        self._active_state = active_state
        self._attr_unique_id: str | None = (
            f"{super().unique_id}::binary_sensor::{self._attribute}"
        )
        self._attr_name: str | None = f"{super().name} {self._attribute}".title()
        self.load_state()

    @override
    def load_state(self):
        self._attr_is_on: bool | None = (
            self.get_str_attr(self._attribute) == self._active_state
        )

    @property
    @override
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return (self._attribute,)


class HubitatHubConnectionBinarySensor(BinarySensorEntity, HubitatEntity):
    """A binary sensor for Hubitat hub connection status."""

    _connection_listener: Callable[[bool], None] | None

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        HubitatEntity.__init__(self, listen_for_device_events=False, **kwargs)
        BinarySensorEntity.__init__(self)

        self._attr_unique_id = f"{self._hub.id}::binary_sensor::hub_status"
        self._attr_name = f"{super().name} Status".title()
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._connection_listener = None
        self.load_state()

    @override
    def load_state(self) -> None:
        """Load current connection state from the hub."""
        self._attr_is_on = self._hub.is_connected

    @override
    async def async_added_to_hass(self) -> None:
        """Listen for hub connection status changes."""
        await super().async_added_to_hass()

        @callback
        def handle_connection_change(connected: bool) -> None:
            self._attr_is_on = connected
            self.async_schedule_update_ha_state()

        self._connection_listener = handle_connection_change
        self._hub.add_connection_listener(handle_connection_change)

    @override
    async def async_will_remove_from_hass(self) -> None:
        """Stop listening for hub connection changes."""
        if self._connection_listener is not None:
            self._hub.remove_connection_listener(self._connection_listener)
            self._connection_listener = None
        await super().async_will_remove_from_hass()

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return hub metadata that was previously in the legacy hub state."""
        return {
            CONF_ID: f"{self._hub.host}::{self._hub.app_id}",
            CONF_HOST: self._hub.host,
            ATTR_HIDDEN: True,
            CONF_TEMPERATURE_UNIT: self._hub.temperature_unit,
            "connection_state": "connected" if self.is_on else "disconnected",
        }


class HubitatAccelerationSensor(HubitatBinarySensor):
    """An acceleration sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.ACCELERATION,
            active_state="active",
            device_class=BinarySensorDeviceClass.MOVING,
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
_SENSOR_ATTRS: tuple[tuple[DeviceAttribute, type[HubitatBinarySensor]], ...] = (
    (DeviceAttribute.ACCELERATION, HubitatAccelerationSensor),
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
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize binary sensor entities."""

    hub = get_hub(hass, config_entry.entry_id)
    hub_entities = [HubitatHubConnectionBinarySensor(hub=hub, device=hub.device)]
    hub.add_entities(hub_entities)
    async_add_entities(hub_entities)

    sensors_added = False

    def add_device_sensors() -> None:
        nonlocal sensors_added
        if sensors_added:
            return
        sensors_added = True

        for attr in _SENSOR_ATTRS:

            def is_sensor(
                device: Device, _overrides: dict[str, str] | None = None
            ) -> bool:
                return attr[0] in device.attributes

            _ = create_and_add_entities(
                hass,
                config_entry,
                async_add_entities,
                "binary_sensor",
                attr[1],
                is_sensor,
            )

    if hub.is_connected:
        add_device_sensors()
    else:

        @callback
        def handle_connection_change(connected: bool) -> None:
            if connected:
                add_device_sensors()
                hub.remove_connection_listener(handle_connection_change)

        hub.add_connection_listener(handle_connection_change)


def _get_contact_info(device: Device) -> ContactInfo:
    """Guess the type of contact sensor from the device's label."""
    label = device.label

    for info in _CONTACT_INFOS:
        if info.matcher.search(label):
            return info

    return _CONTACT_INFOS[len(_CONTACT_INFOS) - 1]


if TYPE_CHECKING:
    from .hub import DEVICE_TYPECHECK, HUB_TYPECHECK

    test_alarm = HubitatBinarySensor(
        hub=HUB_TYPECHECK,
        device=DEVICE_TYPECHECK,
        attribute=DeviceAttribute.CONTACT,
        active_state="open",
    )
