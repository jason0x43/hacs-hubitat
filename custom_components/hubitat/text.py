"""Hubitat Hub Variable text entities."""

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .hub import Hub, get_hub
from .hubitatmaker import HubVariable
from .variable import HubitatVariableEntity


class HubitatVariableText(HubitatVariableEntity, TextEntity):
    """A string Hubitat Hub Variable."""

    def __init__(self, hub: Hub, variable: HubVariable) -> None:
        HubitatVariableEntity.__init__(self, hub, variable, "text")

    @property
    def native_value(self) -> str | None:
        value = self._variable.value
        return None if value is None else str(value)

    @native_value.setter
    def native_value(self, _value: str | None) -> None:
        """Text state is maintained by Hubitat."""

    async def async_set_value(self, value: str) -> None:
        await self._set_value(value)
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = get_hub(hass, entry.entry_id)
    async_add_entities(
        [
            HubitatVariableText(hub, variable)
            for variable in hub.hub_variables.values()
            if variable.type in {"string", "bigdecimal"}
        ]
    )
