from abc import ABC, abstractmethod
from typing import Protocol


class UpdateableEntity(ABC):
    entity_id: str

    @abstractmethod
    def load_state(self) -> None:
        """Load the Hubitat device state into the entity"""
        ...

    @property
    @abstractmethod
    def device_attrs(self) -> tuple[str, ...] | None:
        """Return the device attributes associated with this entity"""
        ...

    @property
    @abstractmethod
    def device_id(self) -> str:
        """Return the Hubitat device ID associated with this entity"""
        ...


class Removable(ABC):
    async def async_will_remove_from_hass(self) -> None:
        """Remove the entity from HA"""
        raise Exception("Must be implemented in a sublcass")


class HasToken(Protocol):
    token: str
