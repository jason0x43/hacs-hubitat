"""The Hubitat integration."""
from asyncio import gather
from copy import deepcopy
from logging import getLogger
from typing import List, Optional

from aiohttp.web import Request
import voluptuous as vol

from homeassistant.components.webhook import async_generate_url
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry

from .const import CONF_APP_ID, DOMAIN
from .hubitat import HubitatHub

_LOGGER = getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["light", "sensor", "binary_sensor"]


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

    host = entry.data.get(CONF_HOST)
    app_id = entry.data.get(CONF_APP_ID)
    token = entry.data.get(CONF_ACCESS_TOKEN)

    hub = HubitatHub(host, app_id, token)
    await hub.connect()

    manager = Hubitat(hub)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = manager

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

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    hass.components.webhook.async_register(
        DOMAIN, "Hubitat", entry.data[CONF_WEBHOOK_ID], handle_event
    )

    hass.async_create_task(
        hub.set_event_url(async_generate_url(hass, entry.data[CONF_WEBHOOK_ID]))
    )

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

    def __init__(self, hub: HubitatHub):
        """Initialize a Hubitat manager."""
        self.hub = hub
        self.entity_ids: List[int] = []


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


async def handle_event(hass: HomeAssistant, webhook_id: str, request: Request):
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

    hub = _get_hub_for_webhook(hass, webhook_id)
    _LOGGER.info(
        f"Received event from {hub} for for {event['displayName']} ({event['deviceId']}) - {event['name']} -> {event['value']}"
    )

    if hub:
        hub.update_state(event)


def _get_hub_for_webhook(hass: HomeAssistant, webhook_id: str) -> Optional[HubitatHub]:
    """Return the hub corresponding to a webhook id."""
    entries = hass.config_entries.async_entries(DOMAIN)
    for entry in entries:
        if entry.data[CONF_WEBHOOK_ID] == webhook_id:
            return hass.data[DOMAIN][entry.entry_id].hub
    return None
