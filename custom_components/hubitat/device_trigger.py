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


from . import DOMAIN
from .const import (
    ATTR_NUM_BUTTONS,
    CAP_HOLDABLE_BUTTON,
    CAP_PUSHABLE_BUTTON,
    CONF_BUTTON_1,
    CONF_BUTTON_2,
    CONF_BUTTON_3,
    CONF_BUTTON_4,
    CONF_HOLD,
    CONF_HUBITAT_EVENT,
    CONF_PUSH,
    CONF_SUBTYPE,
)

TRIGGER_TYPES = {CONF_BUTTON_1, CONF_BUTTON_2, CONF_BUTTON_3, CONF_BUTTON_4}

TRIGGER_SCHEMA = TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),}
)

TRIGGER_CAPABILITIES = {CAP_PUSHABLE_BUTTON, CAP_HOLDABLE_BUTTON}

BUTTON_TRIGGERS = (CONF_BUTTON_1, CONF_BUTTON_2, CONF_BUTTON_3, CONF_BUTTON_4)

_LOGGER = logging.getLogger(__name__)


async def async_validate_trigger_config(hass: HomeAssistant, config: ConfigType):
    """Validate a trigger config."""
    config = TRIGGER_SCHEMA(config)
    device = await get_device(hass, config[CONF_DEVICE_ID])
    trigger = config[CONF_TYPE]

    if (
        not device
        or trigger not in TRIGGER_TYPES
        or not any(
            device_has_capability(hass, device, cap) for cap in TRIGGER_CAPABILITIES
        )
    ):
        raise InvalidDeviceAutomationConfig

    return config


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> List[dict]:
    """List device triggers for Hubitat pushbutton devices."""
    device = await get_device(hass, device_id)
    triggers = []

    if device_has_capability(hass, device, CAP_PUSHABLE_BUTTON):
        num_buttons = get_device_attribute(hass, device, ATTR_NUM_BUTTONS)
        _LOGGER.debug(
            "%s is a pushable button controller with %d buttons",
            device.name,
            num_buttons,
        )
        for i in range(0, num_buttons):
            triggers.append(
                {
                    CONF_DEVICE_ID: device_id,
                    CONF_DOMAIN: DOMAIN,
                    CONF_PLATFORM: "device",
                    CONF_TYPE: BUTTON_TRIGGERS[i],
                    CONF_SUBTYPE: CONF_PUSH,
                }
            )

    if device_has_capability(hass, device, CAP_HOLDABLE_BUTTON):
        num_buttons = get_device_attribute(hass, device, ATTR_NUM_BUTTONS)
        _LOGGER.debug(
            "%s is a holdable button controller with %d buttons",
            device.name,
            num_buttons,
        )
        for i in range(0, num_buttons):
            triggers.append(
                {
                    CONF_DEVICE_ID: device_id,
                    CONF_DOMAIN: DOMAIN,
                    CONF_PLATFORM: "device",
                    CONF_TYPE: BUTTON_TRIGGERS[i],
                    CONF_SUBTYPE: CONF_HOLD,
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

    hubitat_dev_id = get_hubitat_id(device)
    if hubitat_dev_id is None:
        raise InvalidDeviceAutomationConfig

    evt = event.TRIGGER_SCHEMA(
        {
            event.CONF_PLATFORM: "event",
            event.CONF_EVENT_TYPE: CONF_HUBITAT_EVENT,
            event.CONF_EVENT_DATA: {
                CONF_DEVICE_ID: hubitat_dev_id,
                CONF_TYPE: config[CONF_TYPE],
                CONF_SUBTYPE: config[CONF_SUBTYPE],
            },
        }
    )

    _LOGGER.debug(
        "Attached trigger for %s:%s to %s",
        config[CONF_TYPE],
        config[CONF_SUBTYPE],
        device.name,
    )

    return await event.async_attach_trigger(
        hass, evt, action, automation_info, platform_type="device"
    )


async def get_device(hass: HomeAssistant, device_id: str) -> DeviceEntry:
    """Return a Home Assistant device for a given ID."""
    device_registry = await hass.helpers.device_registry.async_get_registry()
    return device_registry.async_get(device_id)


def get_hubitat_id(device: DeviceEntry) -> Optional[str]:
    """Return the Hubitat device ID for a Home Assistant device."""
    device_id = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            return identifier[1]
    return None


def get_device_attribute(hass: HomeAssistant, device: DeviceEntry, attr: str) -> Any:
    """Return the current value of a device attribute."""
    device_id = get_hubitat_id(device)

    if device_id == None:
        _LOGGER.warn("No Hubitat device found for %s", device)
        return None

    for entry in device.config_entries:
        hub = hass.data[DOMAIN][entry].hub
        val = hub.get_device_attribute_value(device_id, attr)
        if val is not None:
            return val

    return None


def device_has_capability(
    hass: HomeAssistant, device: DeviceEntry, capability: str
) -> bool:
    """Return True if a device is known to have a given capability."""
    device_id = get_hubitat_id(device)

    if device_id == None:
        _LOGGER.warn("No Hubitat device found for %s", device)
        return False

    capabilities = None
    for entry in device.config_entries:
        hub = hass.data[DOMAIN][entry].hub
        if hub.device_has_capability(device_id, capability):
            return True

    return False
