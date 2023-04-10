from typing import Any, List, Optional, Sequence, Union

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import ATTR_MODE, DeviceType
from .device import HubitatEntity
from .hub import get_hub
from .types import EntityAdder


class HubitatSelect(HubitatEntity, SelectEntity):
    _attribute: str
    _options: List[str]
    _device_class: str

    @property
    def device_attrs(self) -> Optional[Sequence[str]]:
        """Return this entity's associated attributes"""
        return (self._attribute,)

    @property
    def device_class(self) -> Optional[str]:
        """Return this select's device class."""
        return self._device_class

    @property
    def name(self) -> str:
        """Return this select's display name."""
        return f"{super().name} {self._attribute}".title()

    @property
    def current_option(self) -> Union[str, None]:
        """Return this select's current state."""
        return self.get_str_attr(self._attribute)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return f"{super().unique_id}::sensor::{self._attribute}"

    @property
    def options(self) -> List[str]:
        return self._options or []


class HubitatModeSelect(HubitatSelect):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        # TODO use constant
        self._attribute = ATTR_MODE
        self._device_class = DeviceType.HUB_MODE

    @property
    def options(self) -> List[str]:
        return self._hub.modes or []

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self._hub.set_mode(option)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: EntityAdder,
) -> None:
    """Initialize selectors devices."""

    # If the hub supports modes, add a select for it
    hub = get_hub(hass, entry.entry_id)
    if hub.mode_supported:
        hub_entities = [HubitatModeSelect(hub=hub, device=hub.device)]
        hub.add_entities(hub_entities)
        async_add_entities(hub_entities)
