"""Provide automation triggers for certain types of Hubitat device."""
import logging
from typing import Any, Dict, List, Optional

import voluptuous as vol

from homeassistant.components.automation import AutomationActionType, event
from homeassistant.components.device_automation import TRIGGER_BASE_SCHEMA
from homeassistant.components.device_automation.exceptions import (
    InvalidDeviceAutomationConfig,
)
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
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.typing import ConfigType

from hubitatmaker import (
    Device,
    ATTR_DEVICE_ID,
    ATTR_NAME,
    ATTR_NUM_BUTTONS,
    ATTR_VALUE,
    CAP_DOUBLE_TAPABLE_BUTTON,
    CAP_PUSHABLE_BUTTON,
    CAP_HOLDABLE_BUTTON,
)


from . import DOMAIN
from .const import (
    CONF_BUTTON_1,
    CONF_BUTTON_2,
    CONF_BUTTON_3,
    CONF_BUTTON_4,
    CONF_BUTTON_5,
    CONF_BUTTON_6,
    CONF_BUTTON_7,
    CONF_BUTTON_8,
    CONF_DOUBLE_TAPPED,
    CONF_HELD,
    CONF_HUBITAT_EVENT,
    CONF_PUSHED,
    CONF_SUBTYPE,
    CONF_VALUE,
)

BUTTONS = (
    CONF_BUTTON_1,
    CONF_BUTTON_2,
    CONF_BUTTON_3,
    CONF_BUTTON_4,
    CONF_BUTTON_5,
    CONF_BUTTON_6,
    CONF_BUTTON_7,
    CONF_BUTTON_8,
)

TRIGGER_TYPES = (CONF_DOUBLE_TAPPED, CONF_HELD, CONF_PUSHED)
TRIGGER_SUBTYPES = BUTTONS

TRIGGER_SCHEMA = TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
        vol.Required(CONF_SUBTYPE): vol.In(TRIGGER_SUBTYPES),
    }
)

TRIGGER_CAPABILITIES = {
    CAP_PUSHABLE_BUTTON,
    CAP_HOLDABLE_BUTTON,
    CAP_DOUBLE_TAPABLE_BUTTON,
}

_LOGGER = logging.getLogger(__name__)


async def async_validate_trigger_config(hass: HomeAssistant, config: ConfigType):
    """Validate a trigger config."""
    config = TRIGGER_SCHEMA(config)
    device = await get_device(hass, config[CONF_DEVICE_ID])
    trigger = config[CONF_TYPE]
    button = config[CONF_SUBTYPE]

    # Note that the hubitat domain may not be fully initialized when this
    # function is called, so we can't look use the hub to check actual device
    # capabilities

    if not device or trigger not in TRIGGER_TYPES or button not in TRIGGER_SUBTYPES:
        raise InvalidDeviceAutomationConfig

    return config


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> List[dict]:
    """List device triggers for Hubitat pushbutton devices."""
    device = await get_hubitat_device(hass, device_id)
    if device is None:
        return []

    triggers = []
    types = []
    num_buttons = int(device.attributes[ATTR_NUM_BUTTONS].value)

    if CAP_DOUBLE_TAPABLE_BUTTON in device.capabilities:
        types.append(CONF_DOUBLE_TAPPED)

    if CAP_HOLDABLE_BUTTON in device.capabilities:
        types.append(CONF_HELD)

    if CAP_PUSHABLE_BUTTON in device.capabilities:
        types.append(CONF_PUSHED)

    for event_type in types:
        _LOGGER.debug(
            "%s is a button controller with %d buttons that can be %s",
            device.name,
            num_buttons,
            event_type,
        )

        for i in range(0, num_buttons):
            triggers.append(
                {
                    CONF_DEVICE_ID: device_id,
                    CONF_DOMAIN: DOMAIN,
                    CONF_PLATFORM: "device",
                    CONF_TYPE: event_type,
                    CONF_SUBTYPE: BUTTONS[i],
                }
            )

    _LOGGER.debug("returning triggers: %s", triggers)
    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: AutomationActionType,
    automation_info: dict,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    device = await get_device(hass, config[CONF_DEVICE_ID])
    if device is None:
        raise InvalidDeviceAutomationConfig

    hubitat_device = await get_hubitat_device(hass, config[CONF_DEVICE_ID])
    if hubitat_device is None:
        raise InvalidDeviceAutomationConfig

    evt = event.TRIGGER_SCHEMA(
        {
            event.CONF_PLATFORM: "event",
            event.CONF_EVENT_TYPE: CONF_HUBITAT_EVENT,
            # Event data should match up to what a real event from the hub will
            # contain
            event.CONF_EVENT_DATA: {
                ATTR_DEVICE_ID: hubitat_device.id,
                ATTR_NAME: config[CONF_TYPE],
                ATTR_VALUE: config[CONF_SUBTYPE],
            },
        }
    )

    _LOGGER.debug("Attaching trigger %s", evt)

    return await event.async_attach_trigger(
        hass, evt, action, automation_info, platform_type="device"
    )


async def get_device(hass: HomeAssistant, device_id: str) -> DeviceEntry:
    """Return a Home Assistant device for a given ID."""
    device_registry = await hass.helpers.device_registry.async_get_registry()
    return device_registry.async_get(device_id)


async def get_hubitat_device(hass: HomeAssistant, device_id: str) -> Optional[Device]:
    """Return a Hubitat device for a given Home Assistant device ID."""
    device = await get_device(hass, device_id)

    hubitat_id = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            hubitat_id = identifier[1]
            break

    if hubitat_id is None:
        _LOGGER.debug("Couldn't find Hubitat ID for device %s", device_id)
        return None

    for entry in device.config_entries:
        hub = hass.data[DOMAIN][entry].hub
        if hubitat_id in hub.devices:
            return hub.devices[hubitat_id]

    _LOGGER.debug("Couldn't find Hubitat device for ID %s", hubitat_id)
    return None
