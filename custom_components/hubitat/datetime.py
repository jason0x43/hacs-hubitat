"""Hubitat Hub Variable datetime entities."""

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .hub import Hub, get_hub
from .hubitatmaker import HubVariable
from .variable import HubitatVariableEntity


class HubitatVariableDateTime(HubitatVariableEntity, DateTimeEntity):
    """A DateTime Hubitat Hub Variable."""

    def __init__(self, hub: Hub, variable: HubVariable) -> None:
        HubitatVariableEntity.__init__(self, hub, variable, "datetime")

    @property
    def native_value(self) -> datetime | None:
        value = self._variable.value
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @native_value.setter
    def native_value(self, _value: datetime | None) -> None:
        """DateTime state is maintained by Hubitat."""

    async def async_set_value(self, value: datetime) -> None:
        await self._set_value(value.isoformat())
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = get_hub(hass, entry.entry_id)
    async_add_entities(
        [
            HubitatVariableDateTime(hub, variable)
            for variable in hub.hub_variables.values()
            if variable.type == "datetime"
        ]
    )
