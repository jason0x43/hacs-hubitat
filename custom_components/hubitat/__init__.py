"""The Hubitat integration."""
from asyncio import gather
from logging import getLogger

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant

from .const import CONF_HUBITAT_EVENT, DOMAIN, PLATFORMS
from .device import Hub

_LOGGER = getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Legacy setup -- not implemented."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hubitat from a config entry."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hub = Hub(hass, entry, len(hass.data[DOMAIN]) + 1)

    if not await hub.async_setup():
        return False

    hass.data[DOMAIN][entry.entry_id] = hub

    await hub.async_update_device_registry()

    def stop_hub(event: Event):
        hub.stop()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_hub)

    hass.bus.fire(CONF_HUBITAT_EVENT, {"name": "ready"})
    _LOGGER.info("Hubitat is ready")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = all(
        await gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    hass.data[DOMAIN][entry.entry_id].unload()

    _LOGGER.debug(f"Unloaded all components for {entry.entry_id}")

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
