from typing import Any, Callable, Coroutine, Dict, Mapping, Optional

import voluptuous as vol

from homeassistant.core import HomeAssistant

CONN_CLASS_LOCAL_PUSH: str

class ConfigEntry:
    options: Mapping[str, Any]
    data: Dict[str, Any]
    entry_id: str
    def add_update_listener(
        self,
        listener: Callable[[HomeAssistant, ConfigEntry], Coroutine[Any, Any, None]],
    ) -> Callable[[], None]: ...

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
        data: Dict[str, Any],
        description: Optional[str] = ...,
        description_placeholders: Optional[Dict[str, Any]] = ...,
    ) -> Dict[str, Any]: ...
    def async_show_form(
        self,
        *,
        step_id: str,
        data_schema: Optional[vol.Schema] = ...,
        errors: Optional[Dict[str, Any]] = ...,
        description_placeholders: Optional[Dict[str, Any]] = ...,
    ) -> Dict[str, Any]: ...

class ConfigFlow(_FlowHandler): ...
class OptionsFlow(_FlowHandler): ...
