"""Shared Hubitat Hub Variable entity helpers."""

from homeassistant.helpers.device_registry import DeviceInfo

from .hub import Hub
from .hubitatmaker import Event, HubVariable
from .util import get_device_identifiers


class HubitatVariableEntity:
    """Base entity for a Hubitat Hub Variable."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub: Hub, variable: HubVariable, domain: str) -> None:
        self._hub = hub
        self._variable = variable
        self._attr_name = variable.name
        self._attr_unique_id = f"{hub.id}::hub_variable::{domain}::{variable.name}"
        self._attr_available = variable.available
        self._attr_device_info = DeviceInfo(
            identifiers=get_device_identifiers(hub.id, hub.id),
            name="Hubitat Elevation",
            manufacturer="Hubitat",
        )
        hub.add_hub_variable_listener(variable.name, self._handle_event)

    def _handle_event(self, _event: Event) -> None:
        self._attr_available = self._variable.available
        self.async_write_ha_state()  # type: ignore[attr-defined]

    async def _set_value(self, value: str | float) -> None:
        await self._hub.set_hub_variable(self._variable.name, value)
