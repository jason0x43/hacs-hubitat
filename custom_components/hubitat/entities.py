from logging import getLogger
from typing import Callable, Dict, List, Optional, Type, TypeVar

from custom_components.hubitat.util import get_device_overrides
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry

from .const import DOMAIN
from .device import HubitatEntity, HubitatEventEmitter
from .hub import get_hub
from .hubitatmaker import Device
from .types import EntityAdder

_LOGGER = getLogger(__name__)

E = TypeVar("E", bound=HubitatEntity)


def create_and_add_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: EntityAdder,
    platform: str,
    EntityClass: Type[E],
    is_type: Callable[[Device, Optional[Dict[str, str]]], bool],
) -> List[E]:
    """Create entites and add them to the entity registry."""
    hub = get_hub(hass, config_entry.entry_id)
    devices = hub.devices
    overrides = get_device_overrides(config_entry)

    # Devices that have this entity type
    devices_with_entity = [
        devices[id] for id in devices if is_type(devices[id], overrides)
    ]

    entities: List[E] = [
        EntityClass(hub=hub, device=device) for device in devices_with_entity
    ]

    if len(entities) > 0:
        _migrate_old_unique_ids(hass, entities, platform)
        hub.add_entities(entities)
        async_add_entities(entities)
        _LOGGER.debug(f"Added {EntityClass.__name__} entities: {entities}")

    _LOGGER.debug(f"Removing overridden {platform} entities...")

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
    ereg = entity_registry.async_get(hass)
    entity_ids = {ereg.entities[id].unique_id: id for id in ereg.entities}
    for unique_id in entity_ids:
        if unique_id in entity_unique_ids_to_remove:
            ereg.async_remove(entity_ids[unique_id])
            _LOGGER.debug(f"Removed overridden entity {unique_id}")

    return entities


def create_and_add_event_emitters(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    is_emitter: Callable[[Device], bool],
) -> List[HubitatEventEmitter]:
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


def _migrate_old_unique_ids(
    hass: HomeAssistant, entities: List[E], platform: str
) -> None:
    """Migrate legacy unique IDs to the current format."""
    _LOGGER.debug("Migrating unique_ids for %s...", platform)
    ereg = entity_registry.async_get(hass)
    for entity in entities:
        old_ids = entity.old_unique_ids
        _LOGGER.debug("Checking for existence of entity %s...", old_ids)
        for id in old_ids:
            # The async_get_entity_id args appear not to use standard names
            entity_id = ereg.async_get_entity_id(
                domain=platform, platform=DOMAIN, unique_id=id
            )
            if entity_id is not None:
                _LOGGER.debug("Migrating unique_id for %s", entity_id)
                ereg.async_update_entity(entity_id, new_unique_id=entity.unique_id)
