from logging import getLogger
from typing import Callable, List, Type, TypeVar

from hubitatmaker import Device

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry

from .const import DOMAIN
from .device import HubitatEntity, HubitatEventEmitter, get_hub
from .types import EntityAdder

_LOGGER = getLogger(__name__)

T = TypeVar("T", bound=HubitatEntity)


async def create_and_add_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: EntityAdder,
    platform: str,
    EntityClass: Type[T],
    is_entity: Callable[[Device], bool],
) -> List[T]:
    """Create entites and add them to the entity registry."""
    hub = get_hub(hass, entry.entry_id)
    devices = hub.devices
    entities = [
        EntityClass(hub=hub, device=devices[i])
        for i in devices
        if is_entity(devices[i])
    ]

    if len(entities) > 0:
        await _migrate_old_unique_ids(hass, entities, platform)
        hub.add_entities(entities)
        async_add_entities(entities)
        _LOGGER.debug(f"Added {EntityClass.__name__} entities: {entities}")

    return entities


async def create_and_add_event_emitters(
    hass: HomeAssistant, entry: ConfigEntry, is_emitter: Callable[[Device], bool],
) -> List[HubitatEventEmitter]:
    """Create event emitters."""
    hub = get_hub(hass, entry.entry_id)
    devices = hub.devices
    emitters = [
        HubitatEventEmitter(hub=hub, device=devices[i])
        for i in devices
        if is_emitter(devices[i])
    ]
    print(f"found {len(emitters)} emitters from {hub}")

    for emitter in emitters:
        hass.async_create_task(emitter.update_device_registry())
    hub.add_event_emitters(emitters)
    _LOGGER.debug("Added event emitters: %s", emitters)

    return emitters


async def _migrate_old_unique_ids(
    hass: HomeAssistant, entities: List[T], platform: str
) -> None:
    """Migrate legacy unique IDs to the current format."""
    _LOGGER.debug("Migrating unique_ids for %s...", platform)
    ereg = await entity_registry.async_get_registry(hass)
    for entity in entities:
        old_ids = entity.old_unique_id
        if not isinstance(old_ids, list):
            old_ids = [old_ids]
        _LOGGER.debug("Checking for existence of entity %s...", old_ids)
        for id in old_ids:
            # The async_get_entity_id args appear not to use standard names
            entity_id = ereg.async_get_entity_id(
                domain=platform, platform=DOMAIN, unique_id=id
            )
            if entity_id is not None:
                _LOGGER.debug("Migrating unique_id for %s", entity_id)
                ereg.async_update_entity(entity_id, new_unique_id=entity.unique_id)
