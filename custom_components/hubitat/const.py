"""Constants for the Hubitat integration."""

from hubitatmaker.const import (
    CAP_HOLDABLE_BUTTON,
    CAP_PUSHABLE_BUTTON,
    ATTR_NUM_BUTTONS,
)

DOMAIN = "hubitat"

CONF_APP_ID = "app_id"
CONF_HUB = "hub"
CONF_HUBITAT_EVENT = "hubitat_event"
CONF_SERVER_ADDR = "server_addr"
CONF_SERVER_PORT = "server_port"

CONF_BUTTON_1 = "button_1"
CONF_BUTTON_2 = "button_2"
CONF_BUTTON_3 = "button_3"
CONF_BUTTON_4 = "button_4"
CONF_HOLD = "hold"
CONF_PUSH = "push"
CONF_SUBTYPE = "subtype"

EVENT_DEVICE = "hubitat.device"
EVENT_READY = "hubitat.ready"
