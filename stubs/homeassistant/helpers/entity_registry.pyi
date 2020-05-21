from typing import Optional

from homeassistant.core import HomeAssistant

class RegistryEntry:
    disabled_by: Optional[str]

class EntityRegistry:
    def async_get_entity_id(
        self, domain: str, platform: str, unique_id: str
    ) -> Optional[str]: ...
    def async_update_entity(
        self,
        entity_id: str,
        *,
        name: Optional[str] = None,
        icon: Optional[str] = None,
        new_entity_id: Optional[str] = None,
        new_unique_id: Optional[str] = None,
        disabled_by: Optional[str] = None,
    ) -> RegistryEntry: ...

async def async_get_registry(hass: HomeAssistant) -> EntityRegistry: ...
