from abc import ABC
from typing import Callable, Iterable, Protocol

from homeassistant.helpers.entity import Entity

EntityAdder = Callable[[Iterable[Entity]], None]


class UpdateableEntity(Entity):
    def update_state(self) -> None:
        """Update the entity state in HA"""
        raise Exception("Must be implemented in a sublcass")

    @property
    def device_attrs(self) -> tuple[str, ...] | None:
        """Return the device attributes associated with this entity"""
        raise Exception("Must be implemented in a sublcass")

    @property
    def device_id(self) -> str:
        """Return the Hubitat device ID associated with this entity"""
        raise Exception("Must be implemented in a sublcass")


class Removable(ABC):
    async def async_will_remove_from_hass(self) -> None:
        """Remove the entity from HA"""
        raise Exception("Must be implemented in a sublcass")


class HasToken(Protocol):
    token: str
