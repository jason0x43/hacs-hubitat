import re
from hashlib import sha256

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN, H_CONF_DEVICE_TYPE_OVERRIDES
from .error import DeviceError
from .hubitatmaker.types import Device
from .types import HasToken

_token_hashes: dict[str, str] = {}


def get_token_hash(token: str) -> str:
    if token not in _token_hashes:
        hasher = sha256()
        hasher.update(token.encode("utf-8"))
        _token_hashes[token] = hasher.hexdigest()
    return _token_hashes[token]


def get_hub_short_id(hub: HasToken) -> str:
    return hub.token[:8]


def get_device_overrides(config_entry: ConfigEntry) -> dict[str, str]:
    return config_entry.options.get(H_CONF_DEVICE_TYPE_OVERRIDES, {})


def get_hub_device_id(hub: HasToken, device: str | Device) -> str:
    """Return the hub-relative ID for a device"""
    device_id = device if isinstance(device, str) else device.id
    return f"{get_token_hash(hub.token)}::{device_id}"


def get_hubitat_device_id(device: DeviceEntry) -> str:
    for id_set in device.identifiers:
        if id_set[0] == DOMAIN:
            # The second identifier is hub_id:device_id
            if ":" in id_set[1]:
                return id_set[1].split(":")[1]
            return id_set[1]
    raise DeviceError(f"No Hubitat entry for device {device.id}")


def to_display_name(identifier: str) -> str:
    try:
        if "_" in identifier:
            parts = identifier.split("_")
        else:
            matches = re.finditer(
                ".+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)", identifier
            )
            parts = [m.group(0) for m in matches]
        return " ".join(parts).capitalize()
    except Exception:
        return identifier


def get_device_identifiers(hub_id: str, device_id: str) -> set[tuple[str, str]]:
    """Return the device identifiers."""
    dev_identifier = device_id
    if hub_id != device_id:
        dev_identifier = f"{hub_id}:{device_id}"

    return {(DOMAIN, dev_identifier)}
