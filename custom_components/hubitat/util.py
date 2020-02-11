import logging
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from . import DOMAIN


_LOGGER = logging.getLogger(__name__)


def get_hubitat_device_id(device: DeviceEntry) -> Optional[str]:
    """Return a Hubitat device ID for a Home Assistant device."""
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            return identifier[1]
    return None


def get_device_capabilities(
    hass: HomeAssistant, device: DeviceEntry
) -> Optional[Dict[str, Any]]:
    """Return a list of device capabilities."""
    device_id = get_hubitat_device_id(device)
    if device_id == None:
        _LOGGER.warn("no Hubitat device found for %s", device)

    for entry in device.config_entries:
        hub = hass.data[DOMAIN][entry]
        capabilities = hub.get_device_capabilities(device_id)
        if capabilities:
            return capabilities

    return None


def device_has_capability(
    hass: HomeAssistant, device: DeviceEntry, capability: str
) -> bool:
    """Return True if a device is known to have a given capability."""
    capabilities = get_device_capabilities(hass, device)
    if capabilities:
        for cap in capabilities:
            if cap == capability:
                return True
    return False
