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

DOMAIN = "hubitat"

ATTR_CODES = "codes"
ATTR_CODE_LENGTH = "code_length"
ATTR_CODE_NAME = "code_name"
ATTR_LAST_CODE_NAME = "last_code_name"
ATTR_DOUBLE_TAPPED = "double_tapped"
ATTR_MAX_CODES = "max_codes"

CONF_APP_ID = "app_id"
CONF_HUB = "hub"
CONF_HUBITAT_EVENT = "hubitat_event"
CONF_SERVER_ADDR = "server_addr"
CONF_SERVER_PORT = "server_port"

CONF_BUTTON = "button"
CONF_BUTTONS = ("1", "2", "3", "4", "5", "6", "7", "8")
CONF_DOUBLE_TAPPED = "double_tapped"
CONF_HELD = "held"
CONF_PUSHED = "pushed"
CONF_UNLOCKED_WITH_CODE = "unlocked_with_code"
CONF_SUBTYPE = "subtype"
CONF_VALUE = "value"

PLATFORMS = [
    "binary_sensor",
    "climate",
    "cover",
    "light",
    "lock",
    "sensor",
    "switch",
    "fan",
]

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
