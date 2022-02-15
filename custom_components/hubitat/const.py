"""Constants for the Hubitat integration."""
from typing import Optional, Sequence

from hubitatmaker import (
    ATTR_DOUBLE_TAPPED as HE_ATTR_DOUBLE_TAPPED,
    ATTR_HELD as HE_ATTR_HELD,
    ATTR_LAST_CODE_NAME as HE_ATTR_LAST_CODE_NAME,
    ATTR_PUSHED as HE_ATTR_PUSHED,
    CAP_DOUBLE_TAPABLE_BUTTON,
    CAP_HOLDABLE_BUTTON,
    CAP_LOCK,
    CAP_PUSHABLE_BUTTON,
)

# select entities aren't supported in HA < 2021.7
try:
    import homeassistant.components.select as _  # noqa: F401

    has_select = True
except Exception:
    has_select = False

DOMAIN = "hubitat"

ATTR_ARGUMENTS = "args"
ATTR_ATTRIBUTE = "attribute"
ATTR_ALARM = "alarm"
ATTR_CODE = "code"
ATTR_CODES = "codes"
ATTR_CODE_LENGTH = "code_length"
ATTR_CODE_NAME = "code_name"
ATTR_COLOR_MODE = "color_mode"
ATTR_DELAY = "delay"
ATTR_HA_DEVICE_ID = "ha_device_id"
ATTR_DOUBLE_TAPPED = "double_tapped"
ATTR_ENTRY_DELAY = "entry_delay"
ATTR_EXIT_DELAY = "exit_delay"
ATTR_HSM_STATUS = "hsm_status"
ATTR_HUB = "hub"
ATTR_LAST_CODE_NAME = "last_code_name"
ATTR_LENGTH = "length"
ATTR_MAX_CODES = "max_codes"
ATTR_MODE = "mode"
ATTR_NAME = "name"
ATTR_POSITION = "position"

CONF_APP_ID = "app_id"
CONF_DEVICES = "devices"
CONF_HUB = "hub"
CONF_HUBITAT_EVENT = "hubitat_event"
CONF_DEVICE_LIST = "device_list"
CONF_DEVICE_TYPE_OVERRIDES = "device_type_overrides"
CONF_SERVER_PORT = "server_port"
CONF_SERVER_URL = "server_url"
CONF_USE_SERVER_URL = "use_server_url"
CONF_SERVER_SSL_CERT = "server_ssl_cert"
CONF_SERVER_SSL_KEY = "server_ssl_key"

CONF_BUTTON = "button"
CONF_BUTTONS = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12")
CONF_DOUBLE_TAPPED = "double_tapped"
CONF_HELD = "held"
CONF_PUSHED = "pushed"
CONF_UNLOCKED_WITH_CODE = "code_name"
CONF_SUBTYPE = "subtype"
CONF_VALUE = "value"

DEVICE_TYPE_HUB_MODE = "hub_mode"
DEVICE_TYPE_HUB_HSM_STATUS = "hub_hsm_status"

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

SERVICE_CLEAR_CODE = "clear_code"
SERVICE_SEND_COMMAND = "send_command"
SERVICE_SET_CODE = "set_code"
SERVICE_SET_CODE_LENGTH = "set_code_length"
SERVICE_SET_ENTRY_DELAY = "set_entry_delay"
SERVICE_SET_EXIT_DELAY = "set_exit_delay"
SERVICE_ALARM_SIREN_ON = "alarm_siren_on"
SERVICE_ALARM_STROBE_ON = "alarm_strobe_on"
SERVICE_SET_HSM = "set_hsm"
SERVICE_SET_HUB_MODE = "set_hub_mode"

STEP_USER = "user"
STEP_REMOVE_DEVICES = "remove_devices"
STEP_OVERRIDE_LIGHTS = "override_lights"
STEP_OVERRIDE_SWITCHES = "override_switches"

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


# A mapping from capabilities to the associated Hubitat attributes and HA
# config types
TRIGGER_CAPABILITIES = {
    CAP_PUSHABLE_BUTTON: TriggerInfo(
        HE_ATTR_PUSHED, HE_ATTR_PUSHED, CONF_PUSHED, CONF_BUTTONS
    ),
    CAP_HOLDABLE_BUTTON: TriggerInfo(
        HE_ATTR_HELD, HE_ATTR_HELD, CONF_HELD, CONF_BUTTONS
    ),
    CAP_DOUBLE_TAPABLE_BUTTON: TriggerInfo(
        HE_ATTR_DOUBLE_TAPPED, ATTR_DOUBLE_TAPPED, CONF_DOUBLE_TAPPED, CONF_BUTTONS
    ),
    CAP_LOCK: TriggerInfo(
        HE_ATTR_LAST_CODE_NAME, ATTR_CODE_NAME, CONF_UNLOCKED_WITH_CODE
    ),
}
