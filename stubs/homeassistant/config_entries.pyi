from types import MappingProxyType
from typing import Any, Callable, Dict, Optional

import voluptuous as vol

CONN_CLASS_LOCAL_PUSH: str

class ConfigEntry:
    options: MappingProxyType
    data: dict
    entry_id: str
    def add_update_listener(self, listener: Callable) -> Callable: ...

class ConfigEntries:
    async def async_forward_entry_setup(
        self, entry: ConfigEntry, domain: str
    ) -> bool: ...
    async def async_forward_entry_unload(
        self, entry: ConfigEntry, domain: str
    ) -> bool: ...

class _FlowHandler:
    def async_create_entry(
        self,
        *,
        title: str,
        data: Dict,
        description: Optional[str] = None,
        description_placeholders: Optional[Dict] = None,
    ) -> Dict[str, Any]: ...
    def async_show_form(
        self,
        *,
        step_id: str,
        data_schema: Optional[vol.Schema] = None,
        errors: Optional[Dict] = None,
        description_placeholders: Optional[Dict] = None,
    ) -> Dict[str, Any]: ...

class ConfigFlow(_FlowHandler): ...
class OptionsFlow(_FlowHandler): ...
