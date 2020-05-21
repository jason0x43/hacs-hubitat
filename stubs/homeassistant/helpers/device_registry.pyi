from typing import Any, Dict, Optional, Set, Tuple
from homeassistant.core import HomeAssistant

_UNDEF = object()

CONNECTION_NETWORK_MAC: str
CONNECTION_UPNP: str
CONNECTION_ZIGBEE: str

class DeviceEntry:
    config_entries: Set[str]
    id: str
    identifiers: Set[Tuple[str, str]]

class DeviceRegistry:
    devices: Dict[str, DeviceEntry]
    def async_get(self, device_id: str) -> Optional[DeviceEntry]: ...
    def async_get_or_create(
        self,
        *,
        config_entry_id: str,
        connections: Optional[Set[Any]] = ...,
        identifiers: Optional[Set[Any]] = ...,
        manufacturer: Optional[Any] = ...,
        model: Optional[Any] = ...,
        name: Optional[str] = ...,
        sw_version: Optional[str] = ...,
        entry_type: Optional[str] = ...,
        via_device: Optional[str] = ...
    ) -> Optional[DeviceEntry]: ...

async def async_get_registry(hass: HomeAssistant) -> DeviceRegistry: ...
