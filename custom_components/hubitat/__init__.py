"""The Hubitat integration."""

import re
from asyncio import gather
from logging import getLogger
from typing import Any, cast

import voluptuous as vol

from custom_components.hubitat.services import (
    async_register_services,
    async_remove_services,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant

from .const import DOMAIN, H_CONF_HUBITAT_EVENT, PLATFORMS
from .hub import Hub, get_hub

_LOGGER = getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)


async def async_setup(_hass: HomeAssistant, _config: dict[str, Any]) -> bool:
    """Legacy setup -- not implemented."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Hubitat from a config entry."""

    _LOGGER.debug(f"Setting up Hubitat for {config_entry.entry_id}")

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hub: Hub = await Hub.create(
        hass, config_entry, len(cast(dict[str, Any], hass.data[DOMAIN])) + 1
    )

    hub.async_update_device_registry()

    async_register_services(hass, config_entry)

    def stop_hub(_event: Event) -> None:
        hub.stop()

    _ = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_hub)

    # If this config entry's title uses a MAC address, rename it to use the hub
    # ID
    if re.match(r"Hubitat \(\w{2}(:\w{2}){5}\)", config_entry.title):
        _ = hass.config_entries.async_update_entry(
            config_entry, title=f"Hubitat ({hub.id})"
        )

    hass.bus.fire(H_CONF_HUBITAT_EVENT, {"name": "ready"})
    _LOGGER.info("Hubitat is ready")

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    async_remove_services(hass, config_entry)

    unload_ok = all(
        await gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in PLATFORMS
            ]
        )
    )

    hub = get_hub(hass, config_entry.entry_id)

    hub.stop()
    _LOGGER.debug(f"Stopped event server for {config_entry.entry_id}")

    await hub.unload()
    _LOGGER.debug(f"Unloaded all components for {config_entry.entry_id}")

    if unload_ok:
        cast(dict[str, Any], hass.data[DOMAIN]).pop(config_entry.entry_id)

    return unload_ok
