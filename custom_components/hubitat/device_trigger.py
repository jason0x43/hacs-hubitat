"""Provides device automations for hubitat."""
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
from .const import CAP_PUSHBUTTON, CONF_HUBITAT_EVENT

TRIGGER_TYPES = {"pushed"}

TRIGGER_SCHEMA = TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),}
)

_LOGGER = logging.getLogger(__name__)


async def async_validate_trigger_config(hass: HomeAssistant, config: ConfigType):
    """Validate a trigger config."""
    config = TRIGGER_SCHEMA(config)
    device = await get_device(hass, config[CONF_DEVICE_ID])
    trigger = config[CONF_TYPE]

    if (
        not device
        or trigger not in TRIGGER_TYPES
        or not device_has_capability(hass, device, CAP_PUSHBUTTON)
    ):
        raise InvalidDeviceAutomationConfig

    return config


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> List[dict]:
    """List device triggers for Hubitat pushbutton devices."""
    device = await get_device(hass, device_id)
    triggers = []

    if device_has_capability(hass, device, CAP_PUSHBUTTON):
        triggers.append(
            {
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_PLATFORM: "device",
                CONF_TYPE: "pushed",
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
            event.CONF_EVENT_DATA: {CONF_DEVICE_ID: hubitat_dev_id},
        }
    )

    return await event.async_attach_trigger(
        hass, evt, action, automation_info, platform_type="device"
    )


async def get_device(hass: HomeAssistant, device_id: str):
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


def device_has_capability(
    hass: HomeAssistant, device: DeviceEntry, capability: str
) -> bool:
    """Return True if a device is known to have a given capability."""
    device_id = get_hubitat_id(device)

    if device_id == None:
        _LOGGER.warn("no Hubitat device found for %s", device)
        return False

    capabilities = None
    for entry in device.config_entries:
        hub = hass.data[DOMAIN][entry]
        capabilities = hub.get_device_capabilities(device_id)
        if capabilities:
            break

    if capabilities is None:
        _LOGGER.warn("no capabilities for device %s", device_id)
        return False

    for cap in capabilities:
        if cap == capability:
            return True

    return False
