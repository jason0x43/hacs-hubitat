"""Provide automation triggers for certain types of Hubitat device."""

import logging
from itertools import chain
from json import loads
from typing import Any, Callable, cast

import voluptuous as vol

from custom_components.hubitat.util import get_hubitat_device_id
from homeassistant.components.device_automation.exceptions import (
    InvalidDeviceAutomationConfig,
)
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_EVENT_DATA,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.trigger import (
    TriggerActionType,
    TriggerInfo,
)
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ATTRIBUTE,
    ATTR_DEVICE_ID,
    ATTR_HUB,
    ATTR_VALUE,
    DOMAIN,
    H_CONF_DOUBLE_TAPPED,
    H_CONF_HELD,
    H_CONF_HUBITAT_EVENT,
    H_CONF_PUSHED,
    H_CONF_SUBTYPE,
    H_CONF_UNLOCKED_WITH_CODE,
    TRIGGER_BUTTONS,
    TRIGGER_CAPABILITIES,
)
from .helpers import (
    are_config_entries_loaded,
    get_device_entry_by_device_id,
    get_hub_for_device,
)
from .hub import Hub
from .hubitatmaker import Device, DeviceAttribute, DeviceCapability

try:
    from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
except Exception:
    from homeassistant.components.device_automation import (
        TRIGGER_BASE_SCHEMA,  # type: ignore
    )

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
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
        vol.Required(H_CONF_SUBTYPE): str,
    }
)

_LOGGER = logging.getLogger(__name__)


async def async_validate_trigger_config(
    hass: HomeAssistant, config: dict[str, Any]
) -> dict[str, Any]:
    """Validate a trigger config."""
    config = TRIGGER_SCHEMA(config)
    device = get_device_entry_by_device_id(hass, config[CONF_DEVICE_ID])

    if are_config_entries_loaded(hass, device.id):
        hubitat_device = get_hubitat_device(hass, device.id)
        if hubitat_device:
            types = get_trigger_types(hubitat_device.device)
            trigger_type = config[CONF_TYPE]
            if trigger_type not in types:
                _LOGGER.warning("Device doesn't support '%s'", trigger_type)
                raise InvalidDeviceAutomationConfig

            trigger_subtype = config.get(H_CONF_SUBTYPE)
            if trigger_subtype:
                subtypes = get_trigger_subtypes(hubitat_device.device, trigger_type)
                if not subtypes or trigger_subtype not in subtypes:
                    _LOGGER.warning("Device doesn't support '%s'", trigger_subtype)

    return config


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """list device triggers for Hubitat devices."""
    device = get_hubitat_device(hass, device_id)
    if device is None:
        return []

    triggers = []
    trigger_types = get_trigger_types(device.device)

    for trigger_type in trigger_types:
        trigger_subtypes = get_trigger_subtypes(device.device, trigger_type)

        if trigger_subtypes:
            for trigger_subtype in trigger_subtypes:
                triggers.append(
                    {
                        CONF_DEVICE_ID: device_id,
                        CONF_DOMAIN: DOMAIN,
                        CONF_PLATFORM: "device",
                        CONF_TYPE: trigger_type,
                        H_CONF_SUBTYPE: trigger_subtype,
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
    action: TriggerActionType,
    automation_info: TriggerInfo,
) -> Callable[[], None]:
    """Attach a trigger."""

    hubitat_device = get_hubitat_device(hass, config[CONF_DEVICE_ID])
    if hubitat_device is None:
        _LOGGER.warning(
            "Could not find Hubitat device for ID %s", config[CONF_DEVICE_ID]
        )
        raise InvalidDeviceAutomationConfig

    # Event data should match up to the data a hubitat_event event would
    # contain
    event_data = {
        ATTR_DEVICE_ID: hubitat_device.device.id,
        ATTR_HUB: hubitat_device.hub.id,
        ATTR_ATTRIBUTE: config[CONF_TYPE],
    }
    if H_CONF_SUBTYPE in config:
        event_data[ATTR_VALUE] = config[H_CONF_SUBTYPE]

    trigger = event.TRIGGER_SCHEMA(
        {
            CONF_PLATFORM: "event",
            event.CONF_EVENT_TYPE: H_CONF_HUBITAT_EVENT,
            CONF_EVENT_DATA: event_data,
        }
    )

    _LOGGER.debug("Attaching trigger %s", trigger)

    return await event.async_attach_trigger(
        hass, trigger, action, automation_info, platform_type="device"
    )


class DeviceWrapper:
    def __init__(self, device: Device, hub: Hub):
        self._device = device
        self._hub = hub

    @property
    def device(self):
        return self._device

    @property
    def hub(self):
        return self._hub


def get_hubitat_device(hass: HomeAssistant, device_id: str) -> DeviceWrapper | None:
    """Return a Hubitat device for a given Home Assistant device ID."""
    device = get_device_entry_by_device_id(hass, device_id)
    hubitat_id = get_hubitat_device_id(device)

    hub = get_hub_for_device(hass, device)
    if not hub:
        _LOGGER.warning(f"No Hubitat hub is associated with {device_id}")
        return None
    if hub.devices.get(hubitat_id) is None:
        _LOGGER.warning(f"Invalid Hubitat ID for device {device_id}")
        return None

    return DeviceWrapper(hub.devices[hubitat_id], hub)


def get_trigger_types(device: Device) -> list[str]:
    """Return the list of trigger types for a device."""
    types = []

    if DeviceCapability.DOUBLE_TAPABLE_BUTTON in device.capabilities:
        types.append(H_CONF_DOUBLE_TAPPED)

    if DeviceCapability.HOLDABLE_BUTTON in device.capabilities:
        types.append(H_CONF_HELD)

    if DeviceCapability.PUSHABLE_BUTTON in device.capabilities:
        types.append(H_CONF_PUSHED)

    if DeviceCapability.LOCK in device.capabilities:
        types.append(H_CONF_UNLOCKED_WITH_CODE)

    return types


def get_trigger_subtypes(device: Device, trigger_type: str) -> list[str]:
    """Return the list of trigger subtypes for a device and a trigger type."""
    subtypes: list[str] = []

    if trigger_type in (
        H_CONF_DOUBLE_TAPPED,
        H_CONF_HELD,
        H_CONF_PUSHED,
    ):
        num_buttons = 1
        if DeviceAttribute.NUM_BUTTONS in device.attributes:
            num_buttons = device.attributes[DeviceAttribute.NUM_BUTTONS].int_value
        subtypes.extend(TRIGGER_BUTTONS[0:num_buttons])
    elif trigger_type == H_CONF_UNLOCKED_WITH_CODE:
        subtypes.extend(get_lock_codes(device))

    return subtypes


def get_valid_subtypes(trigger_type: str) -> tuple[str, ...] | None:
    """Return the list of valid trigger subtypes for a given type."""
    for trigger_info in TRIGGER_CAPABILITIES.values():
        if trigger_info.conf == trigger_type:
            return trigger_info.subconfs
    return None


def get_lock_codes(device: Device) -> list[str]:
    """Return the lock codes for a lock."""
    try:
        codes_str = cast(str, device.attributes[DeviceAttribute.LOCK_CODES].value)
        codes = loads(codes_str)
        return [codes[id]["name"] for id in codes]
    except Exception as e:
        _LOGGER.warn("Error getting lock codes for %s: %s", device, e)
        return []
