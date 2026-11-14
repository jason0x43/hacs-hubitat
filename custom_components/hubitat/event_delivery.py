"""Deliver Hubitat events to Home Assistant through a webhook.

Instead of running a standalone event server, the integration can register a
Home Assistant webhook and point Maker API's postURL at it. This works for local
hubs (using Home Assistant's internal URL) and for hubs accessed through the
Hubitat cloud relay (using a Home Assistant Cloud cloudhook or Home Assistant's
external URL).
"""

from collections.abc import Callable
from logging import getLogger
from types import ModuleType
from typing import Any
from urllib.parse import urlparse

from homeassistant.components import webhook
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .hubitatmaker.const import HUBITAT_CLOUD_HOST

_LOGGER = getLogger(__name__)


class NoEventUrlAvailable(HomeAssistantError):
    """Raised when there's no URL the hub can use to reach Home Assistant."""


class CloudNotConnected(HomeAssistantError):
    """Raised when a cloudhook is needed but Home Assistant Cloud isn't connected."""


def _get_cloud(hass: HomeAssistant) -> ModuleType | None:
    """Return the cloud integration module if it's loaded.

    The cloud integration is imported lazily because importing it pulls in
    dependencies that may not be installed when it isn't in use.
    """
    if "cloud" not in hass.config.components:
        return None
    from homeassistant.components import cloud

    return cloud


def _cloud_subscribed(hass: HomeAssistant) -> bool:
    """Return True if Home Assistant Cloud has an active subscription."""
    cloud = _get_cloud(hass)
    return cloud is not None and bool(cloud.async_active_subscription(hass))


def async_listen_cloud_changes(
    hass: HomeAssistant, webhook_id: str, target: Callable[[], None]
) -> list[Callable[[], None]]:
    """Call target when something that affects a cloud hub's event URL changes.

    That's when Home Assistant Cloud connects or disconnects (including logging
    in or out), or when the webhook's cloudhook is created or deleted. Returns
    unsubscribe functions, which is an empty list if the cloud integration isn't
    loaded.
    """
    cloud = _get_cloud(hass)
    if cloud is None:
        return []

    @callback
    def handle_connection_change(_state: Any) -> None:
        target()

    unsubs: list[Callable[[], None]] = [
        cloud.async_listen_connection_change(hass, handle_connection_change)
    ]

    # Not available in older Home Assistant versions
    listen_cloudhook = getattr(cloud, "async_listen_cloudhook_change", None)
    if listen_cloudhook is not None:

        @callback
        def handle_cloudhook_change(_cloudhook: Any) -> None:
            target()

        unsubs.append(listen_cloudhook(hass, webhook_id, handle_cloudhook_change))

    return unsubs


def is_cloud_host(host: str | None) -> bool:
    """Return True if a hub address refers to the Hubitat cloud relay."""
    if not host:
        return False
    return urlparse(host).hostname == HUBITAT_CLOUD_HOST


def can_deliver_cloud_events(hass: HomeAssistant, base_url: str | None) -> bool:
    """Return True if a cloud hub would have some way to reach Home Assistant."""
    if base_url or _cloud_subscribed(hass):
        return True
    try:
        _ = _get_external_url(hass)
    except NoURLAvailableError:
        return False
    return True


async def async_get_event_url(
    hass: HomeAssistant, webhook_id: str, host: str, base_url: str | None
) -> str:
    """Return the URL Hubitat should POST events to.

    base_url:
      A user-provided base URL for Home Assistant that overrides the
      automatically determined one.

    Raises CloudNotConnected if a cloudhook should be used but Home
    Assistant Cloud isn't connected yet, and NoEventUrlAvailable if no usable
    URL could be determined.
    """
    path = webhook.async_generate_path(webhook_id)

    if base_url:
        return f"{base_url.rstrip('/')}{path}"

    if is_cloud_host(host):
        cloud = _get_cloud(hass)
        cloudhook_error: Exception | None = None
        if cloud is not None and cloud.async_active_subscription(hass):
            if not cloud.async_is_connected(hass):
                raise CloudNotConnected("Home Assistant Cloud is not connected")
            try:
                return str(await cloud.async_get_or_create_cloudhook(hass, webhook_id))
            except Exception as e:
                # Fall back to the external URL, if there is one
                _LOGGER.warning("Unable to create a cloudhook: %s", e)
                cloudhook_error = e
        try:
            return f"{_get_external_url(hass)}{path}"
        except NoURLAvailableError as e:
            raise NoEventUrlAvailable(
                "A hub accessed through the Hubitat cloud needs Home Assistant "
                "Cloud or an external URL to send events to"
            ) from (cloudhook_error or e)

    try:
        return f"{_get_internal_url(hass)}{path}"
    except NoURLAvailableError as e:
        raise NoEventUrlAvailable(
            "Unable to determine a local URL for Home Assistant"
        ) from e


async def async_delete_cloudhook(hass: HomeAssistant, webhook_id: str) -> None:
    """Delete the cloudhook for a webhook, if one exists.

    Deleting a cloudhook only updates Home Assistant Cloud's local preferences,
    so it works while the cloud is disconnected.
    """
    cloud = _get_cloud(hass)
    if cloud is None or not cloud.async_is_logged_in(hass):
        return
    try:
        await cloud.async_delete_cloudhook(hass, webhook_id)
    except ValueError:
        # The webhook doesn't have a cloudhook
        pass
    except Exception as e:
        _LOGGER.debug("Unable to delete cloudhook: %s", e)


def _get_external_url(hass: HomeAssistant) -> str:
    return get_url(
        hass,
        allow_internal=False,
        allow_cloud=False,
        prefer_external=True,
    )


def _get_internal_url(hass: HomeAssistant) -> str:
    url = get_url(
        hass,
        allow_external=False,
        allow_cloud=False,
        allow_ip=True,
        prefer_external=False,
    )

    # Hubitat hubs can't resolve mDNS names, so prefer Home Assistant's LAN
    # address over a .local internal URL.
    hostname = urlparse(url).hostname or ""
    api = hass.config.api
    if hostname.endswith(".local") and api is not None and api.local_ip:
        scheme = "https" if api.use_ssl else "http"
        return f"{scheme}://{api.local_ip}:{api.port}"

    return url
