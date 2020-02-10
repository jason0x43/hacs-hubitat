"""Provides device automations for hubitat."""
from typing import List

import voluptuous as vol

from homeassistant.components.automation import AutomationActionType, state
from homeassistant.components.device_automation import TRIGGER_BASE_SCHEMA
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_PLATFORM,
    CONF_TYPE,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry
from homeassistant.helpers.typing import ConfigType

from . import DOMAIN
from .const import CAP_PUSHBUTTON
from .util import device_has_capability

TRIGGER_TYPES = {"pushed"}

TRIGGER_SCHEMA = TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),}
)


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> List[dict]:
    """List device triggers for Hubitat pushbutton devices."""
    registry = await entity_registry.async_get_registry(hass)
    triggers = []

    device_registry = await hass.helpers.device_registry.async_get_registry()
    device = device_registry.async_get(device_id)

    if device_has_capability(hass, device, CAP_PUSHBUTTON):
        triggers.append(
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                # CONF_ENTITY_ID: entry.entity_id,
                CONF_TYPE: "turned_on",
            }
        )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: AutomationActionType,
    automation_info: dict,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    config = TRIGGER_SCHEMA(config)

    # TODO Implement your own logic to attach triggers.
    # Generally we suggest to re-use the existing state or event
    # triggers from the automation integration.

    if config[CONF_TYPE] == "turned_on":
        from_state = STATE_OFF
        to_state = STATE_ON
    else:
        from_state = STATE_ON
        to_state = STATE_OFF

    state_config = {
        state.CONF_PLATFORM: "state",
        CONF_ENTITY_ID: config[CONF_ENTITY_ID],
        state.CONF_FROM: from_state,
        state.CONF_TO: to_state,
    }
    state_config = state.TRIGGER_SCHEMA(state_config)
    return await state.async_attach_trigger(
        hass, state_config, action, automation_info, platform_type="device"
    )
