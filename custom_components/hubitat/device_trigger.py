"""Provide automation triggers for certain types of Hubitat device."""
from itertools import chain
from json import loads
import logging
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, cast

from hubitatmaker import (
    ATTR_DEVICE_ID,
    ATTR_LOCK_CODES,
    ATTR_NUM_BUTTONS,
    ATTR_VALUE,
    CAP_DOUBLE_TAPABLE_BUTTON,
    CAP_HOLDABLE_BUTTON,
    CAP_LOCK,
    CAP_PUSHABLE_BUTTON,
    Device,
)
import voluptuous as vol

from homeassistant.components.automation import AutomationActionType
from homeassistant.components.device_automation.exceptions import (
    InvalidDeviceAutomationConfig,
)
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ATTRIBUTE,
    ATTR_HUB,
    CONF_BUTTONS,
    CONF_DOUBLE_TAPPED,
    CONF_HELD,
    CONF_HUBITAT_EVENT,
    CONF_PUSHED,
    CONF_SUBTYPE,
    CONF_UNLOCKED_WITH_CODE,
    DOMAIN,
    TRIGGER_CAPABILITIES,
)
from .device import Hub, get_hub

try:
    from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
except Exception:
    from homeassistant.components.device_automation import TRIGGER_BASE_SCHEMA  # type: ignore

    DEVICE_TRIGGER_BASE_SCHEMA = TRIGGER_BASE_SCHEMA


# The `event` type moved in HA 0.115
try:
    from homeassistant.components.homeassistant.triggers import event
except ImportError:
    from homeassistant.components.automation import event  # type: ignore


TRIGGER_TYPES = tuple([v.conf for v in TRIGGER_CAPABILITIES.values()])
TRIGGER_SUBTYPES = set(
    chain.from_iterable(
        [v.subconfs for v in TRIGGER_CAPABILITIES.values() if v.subconfs]
    )
)

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES), vol.Required(CONF_SUBTYPE): str}
)

_LOGGER = logging.getLogger(__name__)


async def async_validate_trigger_config(
    hass: HomeAssistant, config: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate a trigger config."""
    config = TRIGGER_SCHEMA(config)

    device = await get_device(hass, config[CONF_DEVICE_ID])
    if not device:
        _LOGGER.warning("Missing device")
        raise InvalidDeviceAutomationConfig

    if DOMAIN in hass.config.components:
        hubitat_device, _ = await get_hubitat_device(hass, device.id)
        if hubitat_device is None:
            _LOGGER.warning("Invalid Hubitat device")
            raise InvalidDeviceAutomationConfig

        types = get_trigger_types(hubitat_device)
        trigger_type = config[CONF_TYPE]
        if trigger_type not in types:
            _LOGGER.warning("Device doesn't support '%s'", trigger_type)
            raise InvalidDeviceAutomationConfig

        trigger_subtype = config.get(CONF_SUBTYPE)
        if trigger_subtype:
            subtypes = get_trigger_subtypes(hubitat_device, trigger_type)
            if not subtypes or trigger_subtype not in subtypes:
                _LOGGER.warning("Device doesn't support '%s'", trigger_subtype)

    return config


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> Sequence[Dict[str, Any]]:
    """List device triggers for Hubitat devices."""
    device, _ = await get_hubitat_device(hass, device_id)
    if device is None:
        return []

    triggers = []
    trigger_types = get_trigger_types(device)

    for trigger_type in trigger_types:
        trigger_subtypes = get_trigger_subtypes(device, trigger_type)

        if trigger_subtypes:
            for trigger_subtype in trigger_subtypes:
                triggers.append(
                    {
                        CONF_DEVICE_ID: device_id,
                        CONF_DOMAIN: DOMAIN,
                        CONF_PLATFORM: "device",
                        CONF_TYPE: trigger_type,
                        CONF_SUBTYPE: trigger_subtype,
                    }
                )
        else:
            triggers.append(
                {
                    CONF_DEVICE_ID: device_id,
                    CONF_DOMAIN: DOMAIN,
                    CONF_PLATFORM: "device",
                    CONF_TYPE: trigger_type,
                }
            )

    _LOGGER.debug("Returning triggers: %s", triggers)
    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: AutomationActionType,
    automation_info: Dict[str, Any],
) -> Callable[[], None]:
    """Attach a trigger."""
    result = await get_hubitat_device(hass, config[CONF_DEVICE_ID])

    hubitat_device = result[0]
    hub = result[1]

    if hubitat_device is None or hub is None:
        _LOGGER.warning(
            "Could not find Hubitat device for ID %s", config[CONF_DEVICE_ID]
        )
        raise InvalidDeviceAutomationConfig

    # Event data should match up to the data a hubitat_event event would
    # contain
    event_data = {
        ATTR_DEVICE_ID: hubitat_device.id,
        ATTR_HUB: hub.id,
        ATTR_ATTRIBUTE: config[CONF_TYPE],
    }
    if CONF_SUBTYPE in config:
        event_data[ATTR_VALUE] = config[CONF_SUBTYPE]

    trigger = event.TRIGGER_SCHEMA(
        {
            event.CONF_PLATFORM: "event",
            event.CONF_EVENT_TYPE: CONF_HUBITAT_EVENT,
            event.CONF_EVENT_DATA: event_data,
        }
    )

    _LOGGER.debug("Attaching trigger %s", trigger)

    return await event.async_attach_trigger(
        hass, trigger, action, automation_info, platform_type="device"
    )


async def get_device(hass: HomeAssistant, device_id: str) -> Optional[DeviceEntry]:
    """Return a Home Assistant device for a given ID."""
    device_registry = await hass.helpers.device_registry.async_get_registry()
    return device_registry.async_get(device_id)


async def get_hubitat_device(
    hass: HomeAssistant, device_id: str
) -> Tuple[Optional[Device], Optional[Hub]]:
    """Return a Hubitat device for a given Home Assistant device ID."""
    device = await get_device(hass, device_id)
    if device is None:
        return None, None

    hubitat_id = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            hubitat_id = identifier[1]
            break

    if hubitat_id is None:
        _LOGGER.debug("Couldn't find Hubitat ID for device %s", device_id)
        return None, None

    for entry_id in device.config_entries:
        hub = get_hub(hass, entry_id)
        if hubitat_id in hub.devices:
            return hub.devices[hubitat_id], hub

    _LOGGER.debug("Couldn't find Hubitat device for ID %s", hubitat_id)
    return None, None


def get_trigger_types(device: Device) -> Sequence[str]:
    """Return the list of trigger types for a device."""
    types = []

    if CAP_DOUBLE_TAPABLE_BUTTON in device.capabilities:
        types.append(CONF_DOUBLE_TAPPED)

    if CAP_HOLDABLE_BUTTON in device.capabilities:
        types.append(CONF_HELD)

    if CAP_PUSHABLE_BUTTON in device.capabilities:
        types.append(CONF_PUSHED)

    if CAP_LOCK in device.capabilities:
        types.append(CONF_UNLOCKED_WITH_CODE)

    return types


def get_trigger_subtypes(device: Device, trigger_type: str) -> Sequence[str]:
    """Return the list of trigger subtypes for a device and a trigger type."""
    subtypes: List[str] = []

    if trigger_type in (CONF_DOUBLE_TAPPED, CONF_HELD, CONF_PUSHED):
        num_buttons = 1
        if ATTR_NUM_BUTTONS in device.attributes:
            num_buttons = int(device.attributes[ATTR_NUM_BUTTONS].value)
        subtypes.extend(CONF_BUTTONS[0:num_buttons])
    elif trigger_type == CONF_UNLOCKED_WITH_CODE:
        subtypes.extend(get_lock_codes(device))

    return subtypes


def get_valid_subtypes(trigger_type: str) -> Optional[Sequence[str]]:
    """Return the list of valid trigger subtypes for a given type."""
    for trigger_info in TRIGGER_CAPABILITIES.values():
        if trigger_info.conf == trigger_type:
            return trigger_info.subconfs
    return None


def get_lock_codes(device: Device) -> Sequence[str]:
    """Return the lock codes for a lock."""
    try:
        codes_str = cast(str, device.attributes[ATTR_LOCK_CODES].value)
        codes = loads(codes_str)
        return [codes[id]["name"] for id in codes]
    except Exception as e:
        _LOGGER.warn("Error getting lock codes for %s: %s", device, e)
        return []
