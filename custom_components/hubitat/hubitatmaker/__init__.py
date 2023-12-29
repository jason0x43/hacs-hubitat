__version__ = "0.6.1"

from .const import (
    DEFAULT_FAN_SPEEDS,
    ID_HSM_STATUS,
    ID_MODE,
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
    DeviceState,
    HubitatColorMode,
)
from .error import ConnectionError, InvalidConfig, InvalidToken, RequestError
from .hub import Hub
from .types import Attribute, Device, Event

__all__ = [
    "Attribute",
    "HubitatColorMode",
    "ConnectionError",
    "DEFAULT_FAN_SPEEDS",
    "Device",
    "DeviceAttribute",
    "DeviceCapability",
    "DeviceCommand",
    "DeviceState",
    "Event",
    "Hub",
    "ID_HSM_STATUS",
    "ID_MODE",
    "InvalidConfig",
    "InvalidToken",
    "RequestError",
]
