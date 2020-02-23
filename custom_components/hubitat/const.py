"""Constants for the Hubitat integration."""

from hubitatmaker import (
    ATTR_DOUBLE_TAPPED,
    ATTR_HELD,
    ATTR_PUSHED,
    CAP_DOUBLE_TAPABLE_BUTTON,
    CAP_PUSHABLE_BUTTON,
    CAP_HOLDABLE_BUTTON,
)

DOMAIN = "hubitat"

CONF_APP_ID = "app_id"
CONF_HUB = "hub"
CONF_HUBITAT_EVENT = "hubitat_event"
CONF_SERVER_ADDR = "server_addr"
CONF_SERVER_PORT = "server_port"

CONF_BUTTON = "button"
CONF_BUTTON_1 = "1"
CONF_BUTTON_2 = "2"
CONF_BUTTON_3 = "3"
CONF_BUTTON_4 = "4"
CONF_BUTTON_5 = "5"
CONF_BUTTON_6 = "6"
CONF_BUTTON_7 = "7"
CONF_BUTTON_8 = "8"
CONF_DOUBLE_TAPPED = "double_tapped"
CONF_HELD = "held"
CONF_PUSHED = "pushed"
CONF_SUBTYPE = "subtype"
CONF_VALUE = "value"

EVENT_DEVICE = "hubitat.device"
EVENT_READY = "hubitat.ready"

PLATFORMS = [
    "binary_sensor",
    "climate",
    "cover",
    "light",
    "sensor",
    "switch",
]

# A mapping from capabilities to the associated Hubitat attributes and HA
# config types
TRIGGER_CAPABILITIES = {
    CAP_PUSHABLE_BUTTON: {"attr": ATTR_PUSHED, "conf": CONF_PUSHED},
    CAP_HOLDABLE_BUTTON: {"attr": ATTR_HELD, "conf": CONF_HELD},
    CAP_DOUBLE_TAPABLE_BUTTON: {"attr": ATTR_DOUBLE_TAPPED, "conf": CONF_DOUBLE_TAPPED},
}
