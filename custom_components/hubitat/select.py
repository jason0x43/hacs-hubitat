from typing import Unpack

from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .device import HubitatEntity, HubitatEntityArgs
from .hub import get_hub
from .types import EntityAdder


class HubitatSelect(HubitatEntity, SelectEntity):
    _attribute: DeviceAttribute

    def __init__(
        self,
        *,
        attribute: DeviceAttribute,
        options: list[str] = [],
        **kwargs: Unpack[HubitatEntityArgs],
    ):
        HubitatEntity.__init__(self, **kwargs)
        SelectEntity.__init__(self)

        self._attr_options = options
        self._attribute = attribute

        # TODO: this should be using ::select:: instead of ::sensor::, but the
        # published integration has been using ::sensor:: for a while now;
        # migrate it at some point
        self._attr_unique_id = f"{super().unique_id}::sensor::{attribute}"

    @property
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return (self._attribute,)

    @property
    def name(self) -> str:
        """Return the display name for this select."""
        return f"{super().name} {self._attribute}".title()

    @property
    def current_option(self) -> str | None:
        """Return this select's current state."""
        return self.get_str_attr(self._attribute)


class HubitatModeSelect(HubitatSelect):
    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        super().__init__(
            attribute=DeviceAttribute.MODE, options=kwargs["hub"].modes or [], **kwargs
        )

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
