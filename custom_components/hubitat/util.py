from hashlib import sha256
from typing import Dict, Union

from custom_components.hubitat.const import CONF_DEVICE_TYPE_OVERRIDES
from hubitatmaker.types import Device

from homeassistant.config_entries import ConfigEntry

from .types import HasToken

_token_hashes = {}


def get_token_hash(token: str) -> str:
    if token not in _token_hashes:
        hasher = sha256()
        hasher.update(token.encode("utf-8"))
        _token_hashes[token] = hasher.hexdigest()
    return _token_hashes[token]


def get_hub_short_id(hub: HasToken) -> str:
    return hub.token[:8]


def get_device_overrides(config_entry: ConfigEntry) -> Dict[str, str]:
    return config_entry.options.get(CONF_DEVICE_TYPE_OVERRIDES, {})


def get_hub_device_id(hub: HasToken, device: Union[str, Device]) -> str:
    """Return the hub-relative ID for a device"""
    device_id = device if isinstance(device, str) else device.id
    return f"{get_token_hash(hub.token)}::{device_id}"
