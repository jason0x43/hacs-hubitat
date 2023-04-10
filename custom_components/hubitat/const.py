"""Constants for the Hubitat integration."""
from typing import Optional, Sequence

from homeassistant.backports.enum import StrEnum

from .hubitatmaker import DeviceAttribute, DeviceCapability

# select entities aren't supported in HA < 2021.7
try:
    import homeassistant.components.select as _  # noqa: F401

    has_select = True
except Exception:
    has_select = False

DOMAIN = "hubitat"


class HassStateAttribute(StrEnum):
    ALARM = "alarm"
    CODES = "codes"
    CODE_LENGTH = "code_length"
    ENTRY_DELAY = "entry_delay"
    EXIT_DELAY = "exit_delay"
    LAST_CODE_NAME = "last_code_name"
    MAX_CODES = "max_codes"


ATTR_ARGUMENTS = "args"
ATTR_ATTRIBUTE = "attribute"
ATTR_CODE = "code"
ATTR_CODE_NAME = "code_name"
ATTR_COLOR_MODE = "color_mode"
ATTR_DELAY = "delay"
ATTR_DEVICE_ID = "device_id"
ATTR_DOUBLE_TAPPED = "double_tapped"
ATTR_HA_DEVICE_ID = "ha_device_id"
ATTR_HSM_STATUS = "hsm_status"
ATTR_HUB = "hub"
ATTR_LENGTH = "length"
ATTR_MODE = "mode"
ATTR_NAME = "name"
ATTR_POSITION = "position"
ATTR_VALUE = "value"


class EventName(StrEnum):
    HELD = "held"
    DOUBLE_TAPPED = "double_tapped"
    PUSHED = "pushed"
    CODE_NAME = "code_name"


H_CONF_ACCESS_TOKEN = "access_token"
H_CONF_APP_ID = "app_id"
H_CONF_DEVICES = "devices"
H_CONF_HOST = "host"
H_CONF_HUB = "hub"
H_CONF_HUBITAT_EVENT = "hubitat_event"
H_CONF_DEVICE_LIST = "device_list"
H_CONF_DEVICE_TYPE_OVERRIDES = "device_type_overrides"
H_CONF_SERVER_PORT = "server_port"
H_CONF_SERVER_URL = "server_url"
H_CONF_USE_SERVER_URL = "use_server_url"
H_CONF_SERVER_SSL_CERT = "server_ssl_cert"
H_CONF_SERVER_SSL_KEY = "server_ssl_key"
H_CONF_BUTTON = "button"
H_CONF_DOUBLE_TAPPED = "double_tapped"
H_CONF_HELD = "held"
H_CONF_PUSHED = "pushed"
H_CONF_UNLOCKED_WITH_CODE = "code_name"
H_CONF_SUBTYPE = "subtype"
H_CONF_VALUE = "value"


class DeviceType(StrEnum):
    HUB_MODE = "hub_mode"
    HUB_HSM_STATUS = "hub_hsm_status"


ICON_ALARM = "mdi:alarm-bell"

PLATFORMS = [
    "alarm_control_panel",
    "binary_sensor",
    "climate",
    "cover",
    "light",
    "lock",
    "sensor",
    "switch",
    "fan",
]

if has_select:
    PLATFORMS.append("select")


class ServiceName(StrEnum):
    CLEAR_CODE = "clear_code"
    SEND_COMMAND = "send_command"
    SET_CODE = "set_code"
    SET_CODE_LENGTH = "set_code_length"
    SET_ENTRY_DELAY = "set_entry_delay"
    SET_EXIT_DELAY = "set_exit_delay"
    ALARM_SIREN_ON = "alarm_siren_on"
    ALARM_STROBE_ON = "alarm_strobe_on"
    SET_HSM = "set_hsm"
    SET_HUB_MODE = "set_hub_mode"


class ConfigStep(StrEnum):
    USER = "user"
    REMOVE_DEVICES = "remove_devices"
    OVERRIDE_LIGHTS = "override_lights"
    OVERRIDE_SWITCHES = "override_switches"


TEMP_F = "F"
TEMP_C = "C"


class TriggerInfo:
    """Trigger metadata."""

    def __init__(
        self, attr: str, event: str, conf: str, subconfs: Optional[Sequence[str]] = None
    ):
        """Initialize a TriggerInfo."""
        self.attr = attr
        self.event = event
        self.conf = conf
        self.subconfs = subconfs


TRIGGER_BUTTONS = (
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
    "12",
)


# A mapping from capabilities to the associated Hubitat attributes and HA
# config types
TRIGGER_CAPABILITIES = {
    DeviceCapability.PUSHABLE_BUTTON: TriggerInfo(
        DeviceAttribute.PUSHED,
        EventName.PUSHED,
        H_CONF_PUSHED,
        TRIGGER_BUTTONS,
    ),
    DeviceCapability.HOLDABLE_BUTTON: TriggerInfo(
        DeviceAttribute.HELD,
        EventName.HELD,
        H_CONF_HELD,
        TRIGGER_BUTTONS,
    ),
    DeviceCapability.DOUBLE_TAPABLE_BUTTON: TriggerInfo(
        DeviceAttribute.DOUBLE_TAPPED,
        EventName.DOUBLE_TAPPED,
        H_CONF_DOUBLE_TAPPED,
        TRIGGER_BUTTONS,
    ),
    DeviceCapability.LOCK: TriggerInfo(
        DeviceAttribute.LAST_CODE_NAME,
        EventName.CODE_NAME,
        H_CONF_UNLOCKED_WITH_CODE,
    ),
}
