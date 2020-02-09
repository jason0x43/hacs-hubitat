"""The Hubitat integration."""
from asyncio import gather
from copy import deepcopy
from logging import getLogger
from typing import Any, List, Optional, cast

from aiohttp.web import Request
import voluptuous as vol
from hubitatmaker import Hub as HubitatHub

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ACCESS_TOKEN,
    CONF_HOST,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import device_registry

from .const import CONF_APP_ID, CONF_SERVER_PORT, DOMAIN, EVENT_READY

_LOGGER = getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["light", "switch", "sensor", "binary_sensor", "climate"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Hubitat component."""

    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=deepcopy(conf)
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Hubitat from a config entry."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    manager = Hubitat(hass, entry, len(hass.data[DOMAIN]) + 1)

    if not await manager.async_setup():
        return False

    hass.data[DOMAIN][entry.entry_id] = manager

    hub = manager.hub

    dreg = await device_registry.async_get_registry(hass)
    dreg.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(device_registry.CONNECTION_NETWORK_MAC, hub.mac)},
        identifiers={(DOMAIN, hub.mac)},
        manufacturer="Hubitat",
        name="Hubitat Elevation",
    )

    def stop_hub(event: Event):
        hub.stop()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_hub)

    hass.bus.fire(EVENT_READY)
    _LOGGER.info("Hubitat is ready")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""

    unload_ok = all(
        await gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    _LOGGER.debug(f"Unloaded all components for {entry.entry_id}")

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class Hubitat:
    """Hubitat management class."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, index: int):
        """Initialize a Hubitat manager."""
        if not CONF_HOST in entry.data:
            raise ValueError(f"Missing host in config entry")
        if not CONF_APP_ID in entry.data:
            raise ValueError(f"Missing app ID in config entry")
        if not CONF_ACCESS_TOKEN in entry.data:
            raise ValueError(f"Missing access token in config entry")

        self.hass = hass
        self.config_entry = entry
        self.entity_ids: List[int] = []

        if index == 1:
            self.hub_entity_id = "hubitat.hub"
        else:
            self.hub_entity_id = f"hubitat.hub_{index}"

        entry.add_update_listener(self.async_update_options)

    @property
    def host(self) -> str:
        return cast(str, self.config_entry.data.get(CONF_HOST))

    @property
    def app_id(self) -> str:
        return cast(str, self.config_entry.data.get(CONF_APP_ID))

    @property
    def token(self) -> str:
        return cast(str, self.config_entry.data.get(CONF_ACCESS_TOKEN))

    async def async_setup(self) -> bool:
        options_port = self.config_entry.options.get(CONF_SERVER_PORT)
        config_port = self.config_entry.data.get(CONF_SERVER_PORT)
        port = options_port if options_port is not None else config_port

        _LOGGER.debug("initializing Hubitat hub with event server on port %s", port)
        self.hub = HubitatHub(self.host, self.app_id, self.token, port)

        await self.hub.start()

        hub = self.hub
        hass = self.hass
        config_entry = self.config_entry

        for component in PLATFORMS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(config_entry, component)
            )
        _LOGGER.debug(f"Registered platforms")

        # Create an entity for the Hubitat hub with basic hub information
        hass.states.async_set(
            self.hub_entity_id,
            "connected",
            {"id": f"{hub.host}::{hub.app_id}", "host": hub.host, "hidden": True,},
        )

        return True

    @staticmethod
    async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
        """Handle options update."""
        hub = hass.data[DOMAIN][entry.entry_id].hub
        port = entry.options.get(CONF_SERVER_PORT, 0)
        _LOGGER.debug("asked to update port event listener port to %s", port)
        if port != hub.port:
            _LOGGER.debug("setting event listener port to %s", port)
            await hub.set_port(port)
