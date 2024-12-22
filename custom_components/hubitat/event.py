"""Hubitat event entities."""

from logging import getLogger
from typing import Unpack, override

from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import EventName
from .device import HubitatEntity, HubitatEntityArgs
from .hub import get_hub
from .hubitatmaker import DeviceAttribute, Event

_LOGGER = getLogger(__name__)

ATTR_EVENTS = {
    DeviceAttribute.PUSHED: EventName.PUSHED,
    DeviceAttribute.HELD: EventName.HELD,
    DeviceAttribute.DOUBLE_TAPPED: EventName.DOUBLE_TAPPED,
    DeviceAttribute.RELEASED: EventName.RELEASED,
}


class HubitatButtonEventEntity(HubitatEntity, EventEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Representation of an Hubitat button event"""

    _button_id: str

    def __init__(self, button_id: str, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a hubitat button event entity"""
        HubitatEntity.__init__(self, device_class=EventDeviceClass.BUTTON, **kwargs)
        EventEntity.__init__(self)

        self._button_id = button_id
        self._attr_unique_id: str | None = (
            f"{super().unique_id}::button_event::{self._button_id}"
        )
        self._attr_name: str | None = f"{super().name} button {self._button_id}".title()
        self._attr_event_types: list[str] = self.get_event_types()

    @override
    def load_state(self):
        pass

    @override
    def handle_event(self, event: Event) -> None:
        if not self.enabled:
            return

        if event.attribute not in ATTR_EVENTS:
            return

        if event.value != self._button_id:
            return

        event_type = ATTR_EVENTS[event.attribute]
        self._trigger_event(event_type)
        self.async_write_ha_state()

    def get_event_types(self) -> list[str]:
        return [
            ATTR_EVENTS[attr] for attr in self._device.attributes if attr in ATTR_EVENTS
        ]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize hubitat button events entities."""
    hub = get_hub(hass, config_entry.entry_id)

    event_entities: list[HubitatButtonEventEntity] = []
    for id in hub.devices:
        device = hub.devices[id]
        if DeviceAttribute.NUM_BUTTONS not in device.attributes:
            continue

        num_buttons = device.attributes[DeviceAttribute.NUM_BUTTONS].int_value
        if num_buttons is None:
            continue

        for i in range(1, num_buttons + 1):
            event_entities.append(
                HubitatButtonEventEntity(button_id=str(i), hub=hub, device=device)
            )

    if len(event_entities) > 0:
        hub.add_entities(event_entities)
        async_add_entities(event_entities)
