from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN
from .error import DeviceError
from .hub import Hub


def are_config_entries_loaded(hass: HomeAssistant, device_id: str) -> bool:
    """Return true if all of a device's config entries are loaded"""
    device = get_device_entry_by_device_id(hass, device_id)
    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry or entry.state != ConfigEntryState.LOADED:
            return False
    return True


def get_device_entry_by_device_id(
    hass: HomeAssistant, device_id: str
) -> DeviceEntry:
    """Get the device entry for a given device ID."""
    dreg = device_registry.async_get(hass)
    device = dreg.async_get(device_id)
    if device is None:
        raise DeviceError(f"Device {device_id} is not a valid device.")
    return device


def get_hub_for_device(hass: HomeAssistant, device: DeviceEntry) -> Hub | None:
    """Get the Hubitat hub associated with a device."""
    for entry_id in device.config_entries:
        hub = get_hub(hass, entry_id)
        if hub:
            return hub
    return None


def get_hub(hass: HomeAssistant, config_entry_id: str) -> Hub:
    """Get the Hub device associated with a given config entry."""
    return hass.data[DOMAIN].get(config_entry_id)
