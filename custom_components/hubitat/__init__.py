"""The Hubitat integration."""

import asyncio
import contextlib
import re
from datetime import timedelta
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

from .const import (
    DOMAIN,
    H_CONF_HUB_ID,
    H_CONF_HUBITAT_EVENT,
    H_CONF_LEGACY_LIGHT_NAME_HEURISTIC,
    PLATFORMS,
    Platform,
)
from .hub import Hub, get_domain_data, get_hub
from .hubitatmaker.error import (
    ConnectionError as HubitatConnectionError,
    InvalidConfig,
    InvalidToken,
)

_EXPECTED_ERRORS = (
    asyncio.TimeoutError,
    ConnectionError,
    HubitatConnectionError,
    InvalidToken,
    InvalidConfig,
)
_LOGGER = getLogger(__name__)
_HUB_STATUS_PLATFORMS: tuple[Platform, ...] = ("binary_sensor",)


# Interval between hub connection attempts until the first successful connect
RETRY_CONNECT_INTERVAL = timedelta(seconds=90)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry to new version."""
    _LOGGER.debug("Migrating config entry from version %s", config_entry.version)

    new_data = {**config_entry.data}
    version = config_entry.version
    minor_version = config_entry.minor_version
    unique_id: str | None = None

    if version == 1:
        # Generate hub_id from current token (preserves existing IDs)
        token: str | None = config_entry.data.get(CONF_ACCESS_TOKEN)
        if token:
            hub_id = str(token)[:8]
            new_data[H_CONF_HUB_ID] = hub_id
            version = 2
            unique_id = hub_id
            _LOGGER.info("Migrated config entry to version 2 with hub_id=%s", hub_id)
        else:
            _LOGGER.error("Cannot migrate config entry: no access token found")
            return False

    if minor_version < 2:
        # Preserve the historic label-based classification for existing entries.
        new_data[H_CONF_LEGACY_LIGHT_NAME_HEURISTIC] = True
        minor_version = 2

    if (
        new_data != config_entry.data
        or version != config_entry.version
        or minor_version != config_entry.minor_version
    ):
        update_kwargs: dict[str, Any] = {
            "data": new_data,
            "version": version,
            "minor_version": minor_version,
        }
        if unique_id is not None:
            update_kwargs["unique_id"] = unique_id
        hass.config_entries.async_update_entry(config_entry, **update_kwargs)

    return True


async def async_setup(_hass: HomeAssistant, _config: dict[str, Any]) -> bool:
    """Legacy setup -- not implemented."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Hubitat from a config entry."""

    _LOGGER.debug(f"Setting up Hubitat for {config_entry.entry_id}")

    domain_data = get_domain_data(hass)

    # Create an offline hub so there is always an object to clean up, even if
    # the connection never succeeds
    hub = await Hub.create_offline(hass, config_entry, len(domain_data) + 1)
    await hass.config_entries.async_forward_entry_setups(
        config_entry, _HUB_STATUS_PLATFORMS
    )
    hub.mark_platforms_setup(_HUB_STATUS_PLATFORMS)

    async_register_services(hass, config_entry)

    def stop_hub(_event: Event) -> None:
        hub.stop()

    _ = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_hub)

    # Connect in the background so setup returns immediately, even if the hub
    # takes a long time to load its devices. Home Assistant cancels the task
    # automatically when the config entry is unloaded.
    task = config_entry.async_create_background_task(
        hass,
        _async_connect_loop(hass, config_entry, hub),
        name=f"hubitat_connect_{config_entry.entry_id}",
        eager_start=False,
    )
    hub.set_connect_task(task)

    return True


async def _async_connect_loop(
    hass: HomeAssistant, config_entry: ConfigEntry, hub: Hub
) -> None:
    """Connect to the hub, retrying every RETRY_CONNECT_INTERVAL until connected.

    Attempts run sequentially inside this single task, so they can never overlap.
    CancelledError is not caught here, so unload cancels the task cleanly.
    """
    last_error: str | None = None
    while True:
        try:
            await hub.async_connect()
        except Exception as e:  # CancelledError is a BaseException, so it propagates
            hub.set_connected(False)
            error = f"{type(e).__name__}: {e}"
            if error != last_error:
                last_error = error
                if isinstance(e, _EXPECTED_ERRORS):
                    _LOGGER.warning(
                        "Unable to connect to Hubitat hub (will retry): %s", error
                    )
                else:
                    _LOGGER.exception(
                        "Unexpected error connecting to Hubitat hub (will retry)"
                    )
            else:
                _LOGGER.debug("Connection attempt failed again: %s", error)
        else:
            _LOGGER.info("Successfully connected to Hubitat hub")
            _on_hub_connected(hass, config_entry, hub)
            return

        await asyncio.sleep(RETRY_CONNECT_INTERVAL.total_seconds())


def _on_hub_connected(hass: HomeAssistant, config_entry: ConfigEntry, hub: Hub) -> None:
    """Rename MAC-based titles and announce readiness once connected."""
    if re.match(r"Hubitat \(\w{2}(:\w{2}){5}\)", config_entry.title):
        _ = hass.config_entries.async_update_entry(
            config_entry, title=f"Hubitat ({hub.id})"
        )

    hass.bus.fire(H_CONF_HUBITAT_EVENT, {"name": "ready"})
    _LOGGER.info("Hubitat is ready")


async def _cancel_connect_task(hub: Hub) -> None:
    """Cancel the background connect task and wait for it to finish."""
    task = hub.get_connect_task()
    if task is None or task.done():
        return
    _ = task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    async_remove_services(hass, config_entry)

    hub = get_hub(hass, config_entry.entry_id)

    # Stop the connect loop first so it can't finish connecting, or forward
    # platforms, while we're tearing the hub down.
    await _cancel_connect_task(hub)

    platforms_to_unload = tuple(
        p for p in PLATFORMS if p not in hub.get_unsetup_platforms()
    )

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in platforms_to_unload
            ]
        )
    )

    hub.stop()
    _LOGGER.debug(f"Stopped event server for {config_entry.entry_id}")

    await hub.unload()
    _LOGGER.debug(f"Unloaded all components for {config_entry.entry_id}")

    if unload_ok:
        get_domain_data(hass).pop(config_entry.entry_id)

    return unload_ok
