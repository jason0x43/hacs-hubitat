from typing import Any, Callable, Dict, Optional

import voluptuous

from homeassistant.components.automation import AutomationActionType
from homeassistant.core import HomeAssistant

CONF_EVENT_DATA: str
CONF_EVENT_TYPE: str
CONF_PLATFORM: str
TRIGGER_SCHEMA: voluptuous.Schema

async def async_attach_trigger(
    hass: HomeAssistant,
    config: Dict[str, Any],
    action: AutomationActionType,
    automation_info: Dict[str, Any],
    *,
    platform_type: Optional[str] = "event"
) -> Callable[[], None]: ...
