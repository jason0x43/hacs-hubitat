"""The Hubitat integration."""
from asyncio import gather
from copy import deepcopy
from logging import getLogger
from typing import Any, List, Optional, cast

from aiohttp.web import Request
import voluptuous as vol
from hubitatmaker import Hub as HubitatHub

from homeassistant.components.webhook import async_generate_url
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ACCESS_TOKEN,
    CONF_HOST,
    CONF_WEBHOOK_ID,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry

from .const import CONF_APP_ID, DOMAIN, EVENT_READY

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
        identifiers={(DOMAIN, hub.id)},
        manufacturer="Hubitat",
        name=hub.name,
        model=hub.hw_version,
        sw_version=hub.sw_version,
    )

    hass.bus.fire(EVENT_READY)
    _LOGGER.info("Hubitat is ready")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""

    hass.components.webhook.async_unregister(entry.data[CONF_WEBHOOK_ID])
    _LOGGER.debug(f"Unregistered webhook {entry.data[CONF_WEBHOOK_ID]}")

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
        self.hub = HubitatHub(self.host, self.app_id, self.token)

        await self.hub.start()

        hub = self.hub
        hass = self.hass
        config_entry = self.config_entry

        for component in PLATFORMS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(config_entry, component)
            )
        _LOGGER.debug(f"Registered platforms")

        webhook_id = config_entry.data[CONF_WEBHOOK_ID]

        hass.components.webhook.async_register(
            DOMAIN, "Hubitat", webhook_id, self.handle_event
        )
        _LOGGER.debug(f"Registered webhook {webhook_id}")

        hass.async_create_task(hub.set_event_url(async_generate_url(hass, webhook_id)))
        _LOGGER.debug(f"Set event POST URL")

        # Create an entity for the Hubitat hub with basic hub information
        hass.states.async_set(
            self.hub_entity_id,
            "connected",
            {
                "id": hub.id,
                "host": hub.host,
                "sw_version": hub.sw_version,
                "hidden": True,
            },
        )

        return True

    async def handle_event(
        self, hass: HomeAssistant, webhook_id: str, request: Request
    ):
        """Handle an event from the hub."""
        try:
            data = await request.json()
            event = EVENT_SCHEMA(data)["content"]
        except Exception as e:
            _LOGGER.warning(f"Invalid message from Hubitat: {e}")
            return None

        if event["name"] == "ssdpTerm":
            # Ignore upnp events
            return

        _LOGGER.debug(
            f"Received event from {self.hub} for for {event['displayName']} ({event['deviceId']}) - {event['name']} -> {event['value']}"
        )

        self.hub.process_event(event)


EVENT_SCHEMA = vol.Schema(
    {
        "content": {
            "name": str,
            "value": vol.Any(str, int),
            "deviceId": vol.Any(None, str),
            "displayName": vol.Any(None, str),
            "descriptionText": vol.Any(None, str),
            "unit": vol.Any(None, str),
            "data": vol.Any(None, dict, list, int, str),
        }
    },
    required=True,
)
