"""The Hubitat integration."""

import asyncio
import re
from datetime import datetime, timedelta
from logging import getLogger
from typing import Any

import voluptuous as vol

from custom_components.hubitat.services import (
    async_register_services,
    async_remove_services,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, H_CONF_HUB_ID, H_CONF_HUBITAT_EVENT, PLATFORMS
from .hub import Hub, get_domain_data, get_hub

_LOGGER = getLogger(__name__)

# Time to attempt initial hub connection during startup
STARTUP_CONNECT_TIMEOUT = 60  # seconds

# Interval for retrying hub connection after startup failure
RETRY_CONNECT_INTERVAL = timedelta(seconds=90)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry to new version."""
    _LOGGER.debug("Migrating config entry from version %s", config_entry.version)

    if config_entry.version == 1:
        # Generate hub_id from current token (preserves existing IDs)
        new_data = {**config_entry.data}
        token: str | None = config_entry.data.get(CONF_ACCESS_TOKEN)
        if token:
            hub_id = str(token)[:8]
            new_data[H_CONF_HUB_ID] = hub_id

            hass.config_entries.async_update_entry(
                config_entry,
                data=new_data,
                version=2,
                unique_id=hub_id,
            )
            _LOGGER.info("Migrated config entry to version 2 with hub_id=%s", hub_id)
        else:
            _LOGGER.error("Cannot migrate config entry: no access token found")
            return False

    return True


async def async_setup(_hass: HomeAssistant, _config: dict[str, Any]) -> bool:
    """Legacy setup -- not implemented."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Hubitat from a config entry."""

    _LOGGER.debug(f"Setting up Hubitat for {config_entry.entry_id}")

    domain_data = get_domain_data(hass)

    # Try to connect to the hub with a timeout
    hub: Hub | None = None

    # First create an offline hub to get a HubitatHub instance we can cleanup
    # if the connection attempt times out
    hub = await Hub.create_offline(hass, config_entry, len(domain_data) + 1)

    try:
        # Try to connect with timeout
        await asyncio.wait_for(hub.async_connect(), timeout=STARTUP_CONNECT_TIMEOUT)

        hub.async_update_device_registry()

        _LOGGER.info("Successfully connected to Hubitat hub")

    except (asyncio.TimeoutError, ConnectionError) as e:
        _LOGGER.warning(
            "Unable to connect to Hubitat hub during startup (will retry): %s", e
        )

        # Schedule periodic connection attempts
        async def retry_connection(_now: datetime | None = None) -> None:
            """Attempt to reconnect to the hub."""
            if not hub.is_connected:
                _LOGGER.debug("Attempting to reconnect to Hubitat hub...")
                try:
                    await asyncio.wait_for(
                        hub.async_connect(), timeout=STARTUP_CONNECT_TIMEOUT
                    )
                    _LOGGER.info("Successfully reconnected to Hubitat hub")
                    hub.async_update_device_registry()

                    # Cancel the retry task now that we're connected
                    hub.cancel_retry_task()

                    # Fire ready event now that we're connected
                    hass.bus.fire(H_CONF_HUBITAT_EVENT, {"name": "ready"})

                    # Update hub state
                    if re.match(r"Hubitat \(\w{2}(:\w{2}){5}\)", config_entry.title):
                        _ = hass.config_entries.async_update_entry(
                            config_entry, title=f"Hubitat ({hub.id})"
                        )

                    hass.states.async_set(
                        hub.entity_id,
                        "connected",
                        hub.get_state_attributes(),
                    )
                except (asyncio.TimeoutError, ConnectionError) as e:
                    _LOGGER.debug("Reconnection attempt failed: %s", e)
                    hass.states.async_set(
                        hub.entity_id,
                        "unavailable",
                        hub.get_state_attributes(),
                    )

        # Retry immediately once, then periodically
        _ = hass.async_create_task(retry_connection())
        unsub = async_track_time_interval(
            hass, retry_connection, RETRY_CONNECT_INTERVAL
        )
        hub.set_retry_task_unsub(unsub)

    async_register_services(hass, config_entry)

    def stop_hub(_event: Event) -> None:
        hub.stop()

    _ = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_hub)

    # If this config entry's title uses a MAC address, rename it to use the hub
    # ID (only if hub is connected)
    if hub.is_connected and re.match(
        r"Hubitat \(\w{2}(:\w{2}){5}\)", config_entry.title
    ):
        _ = hass.config_entries.async_update_entry(
            config_entry, title=f"Hubitat ({hub.id})"
        )

    if hub.is_connected:
        hass.bus.fire(H_CONF_HUBITAT_EVENT, {"name": "ready"})
        _LOGGER.info("Hubitat is ready")

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    async_remove_services(hass, config_entry)

    unload_ok = all(
        await asyncio.gather(
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
        get_domain_data(hass).pop(config_entry.entry_id)

    return unload_ok
