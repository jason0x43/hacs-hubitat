from logging import getLogger
from typing import Callable, TypeVar

from custom_components.hubitat.const import Platform
from custom_components.hubitat.util import get_device_overrides
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device import HubitatEntity, HubitatEventEmitter
from .hub import get_hub
from .hubitatmaker import Device

_LOGGER = getLogger(__name__)

E = TypeVar("E", bound=HubitatEntity)


def create_and_add_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    platform: Platform,
    EntityClass: type[E],
    is_type: Callable[[Device, dict[str, str] | None], bool],
) -> list[E]:
    """Create entites and add them to the entity registry."""
    hub = get_hub(hass, config_entry.entry_id)
    devices = hub.devices
    overrides = get_device_overrides(config_entry)

    # Devices that have this entity type
    devices_with_entity = [
        devices[id] for id in devices if is_type(devices[id], overrides)
    ]

    entities: list[E] = [
        EntityClass(hub=hub, device=device) for device in devices_with_entity
    ]

    if len(entities) > 0:
        hub.add_entities(entities)
        async_add_entities(entities)

    # Devices that have this entity type when not overridden
    original_devices_with_entity = [
        devices[id] for id in devices if is_type(devices[id], None)
    ]

    # Remove any existing entities that were overridden
    entity_unique_ids_to_remove = [
        EntityClass(hub=hub, device=d, temp=True).unique_id
        for d in original_devices_with_entity
        if d not in devices_with_entity
    ]

    if len(entity_unique_ids_to_remove) > 0:
        _LOGGER.debug(f"Removing overridden {platform} entities...")
        ereg = entity_registry.async_get(hass)
        entity_ids = {ereg.entities[id].unique_id: id for id in ereg.entities}
        for unique_id in entity_ids:
            if unique_id in entity_unique_ids_to_remove:
                ereg.async_remove(entity_ids[unique_id])
                _LOGGER.debug(f"Removed overridden entity {entity_ids[unique_id]}")

    return entities


def create_and_add_event_emitters(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    is_emitter: Callable[[Device], bool],
) -> list[HubitatEventEmitter]:
    """Create event emitters."""
    hub = get_hub(hass, config_entry.entry_id)
    devices = hub.devices
    emitters = [
        HubitatEventEmitter(hub=hub, device=devices[i])
        for i in devices
        if is_emitter(devices[i])
    ]

    for emitter in emitters:
        emitter.update_device_registry()
    hub.add_event_emitters(emitters)
    _LOGGER.debug("Added event emitters: %s", emitters)

    return emitters
