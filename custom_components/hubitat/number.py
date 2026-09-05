"""Hubitat Hub Variable number entities."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .hub import get_hub
from .hubitatmaker import HubVariable
from .variable import HubitatVariableEntity

_NUMBER_TYPES = {"integer"}


class HubitatVariableNumber(HubitatVariableEntity, NumberEntity):
    """A numeric Hubitat Hub Variable."""

    _attr_mode = NumberMode.BOX
    _attr_native_min_value = -(2**31)
    _attr_native_max_value = 2**31 - 1

    def __init__(self, hub, variable: HubVariable) -> None:
        HubitatVariableEntity.__init__(self, hub, variable, "number")
        self._attr_native_step = 1

    @property
    def native_value(self) -> float | None:
        try:
            return float(self._variable.value)
        except TypeError:
            return None
        except ValueError:
            return None

    @native_value.setter
    def native_value(self, _value: float | None) -> None:
        """Number state is maintained by Hubitat."""

    async def async_set_native_value(self, value: float) -> None:
        await self._set_value(str(int(value)))
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = get_hub(hass, entry.entry_id)
    async_add_entities(
        [
            HubitatVariableNumber(hub, variable)
            for variable in hub.hub_variables.values()
            if variable.type in _NUMBER_TYPES
        ]
    )
