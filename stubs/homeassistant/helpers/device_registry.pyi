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
        connections: Optional[set] = None,
        identifiers: Optional[set] = None,
        manufacturer: Optional[Any] = None,
        model: Optional[Any] = None,
        name: Optional[str] = None,
        sw_version: Optional[str] = None,
        entry_type: Optional[str] = None,
        via_device: Optional[str] = None
    ) -> Optional[DeviceEntry]: ...

async def async_get_registry(hass: HomeAssistant) -> DeviceRegistry: ...
