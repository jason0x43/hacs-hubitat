from typing import Callable, Iterable, List, Optional, Protocol

from homeassistant.helpers.entity import Entity

EntityAdder = Callable[[Iterable[Entity]], None]


class UpdateableEntity(Entity):
    def update_state(self):
        """Update the entity state in HA"""
        raise Exception("Must be implemented in a sublcass")

    @property
    def device_attrs(self) -> Optional[List[str]]:
        """Return the device attributes associated with this entity"""
        raise Exception("Must be implemented in a sublcass")

    @property
    def device_id(self) -> str:
        """Return the Hubitat device ID associated with this entity"""
        raise Exception("Must be implemented in a sublcass")


class Removable(Protocol):
    async def async_will_remove_from_hass(self):
        """Remove the entity from HA"""
        raise Exception("Must be implemented in a sublcass")


class HasToken(Protocol):
    token: str
