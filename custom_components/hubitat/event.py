"""Hubitat event entities."""

from logging import getLogger
from typing import Unpack

from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    _TRIGGER_ATTRS,
    _TRIGGER_ATTR_MAP,
)
from .device import HubitatEntity, HubitatEntityArgs
from .hub import get_hub
from .hubitatmaker import DeviceAttribute, Event
from .types import EntityAdder

_LOGGER = getLogger(__name__)


class HubitatButtonEvent(HubitatEntity, EventEntity):
    """Representation of an Hubitat button event"""

    _button_id: str

    def __init__(self, button_id: str, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a hubitat button event entity"""
        HubitatEntity.__init__(self, device_class=EventDeviceClass.BUTTON, **kwargs)
        EventEntity.__init__(self)

        self._button_id = button_id
        self._attr_unique_id = f"{super().unique_id}::button_event::{self._button_id}"
        self._attr_event_types = self.get_event_types()

    @property
    def name(self) -> str:
        """Return the display name for this button event entity."""
        return f"{super().name} button {self._button_id}".title()

    def handle_event(self, event: Event) -> None:
        if self.is_disabled:
            return

        if event.attribute not in _TRIGGER_ATTRS:
            return

        if event.value != self._button_id:
            return

        event_type = _TRIGGER_ATTR_MAP[event.attribute]
        self._trigger_event(event_type)
        self.async_write_ha_state()

    def get_event_types(self) -> list[str]:
        event_attrs = filter(
            lambda attr: attr in self._device.attributes,
            _TRIGGER_ATTRS
        )
        event_types = map(
            lambda attr: _TRIGGER_ATTR_MAP[attr],
            list(event_attrs)
        )
        return list(event_types)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: EntityAdder,
) -> None:
    """Initialize hubitat button events entities."""
    hub = get_hub(hass, config_entry.entry_id)

    event_entities = []
    for id in hub.devices:
        device = hub.devices[id]
        if DeviceAttribute.NUM_BUTTONS not in device.attributes:
            continue

        num_buttons = device.attributes[DeviceAttribute.NUM_BUTTONS].int_value
        if num_buttons is None:
            continue

        for i in range(1, num_buttons + 1):
            event_entities.append(
                HubitatButtonEvent(
                    button_id=str(i),
                    hub=hub,
                    device=device
                )
            )

    if len(event_entities) > 0:
        hub.add_entities(event_entities)
        async_add_entities(event_entities)
        _LOGGER.debug(f"Added button event entities: {event_entities}")
