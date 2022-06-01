from hubitatmaker import (
    ATTR_DOOR,
    ATTR_LEVEL,
    ATTR_POSITION,
    ATTR_WINDOW_SHADE,
    CAP_DOOR_CONTROL,
    CAP_GARAGE_DOOR_CONTROL,
    CAP_WINDOW_SHADE,
    CMD_CLOSE,
    CMD_OPEN,
    CMD_SET_POSITION,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
    STATE_PARTIALLY_OPEN,
    Device,
)
from logging import getLogger
from typing import Any, Dict, List, Optional, Tuple, Type

from homeassistant.components.cover import (
    ATTR_POSITION as HA_ATTR_POSITION,
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_GARAGE,
    DEVICE_CLASS_SHADE,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    CoverEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .device import HubitatEntity
from .entities import create_and_add_entities
from .types import EntityAdder

_LOGGER = getLogger(__name__)


class HubitatCover(HubitatEntity, CoverEntity):
    """Representation of a Hubitat cover."""

    _attribute: str
    _features: int
    _device_class: Optional[str]

    @property
    def device_class(self) -> Optional[str]:
        """Return this sensor's device class."""
        return self._device_class

    @property
    def current_cover_position(self) -> Optional[int]:
        """Return current position of cover."""
        pos = self.get_int_attr(ATTR_POSITION)
        if pos is not None:
            return pos
        # At least the Qubino Roller Shutter driver reports the shade position
        # using the 'level' parameter
        return self.get_int_attr(ATTR_LEVEL)

    @property
    def is_closed(self) -> bool:
        """Return True if the cover is closed."""
        return self.get_attr(self._attribute) == STATE_CLOSED

    @property
    def is_closing(self) -> bool:
        """Return True if the cover is opening."""
        return self.get_attr(self._attribute) == STATE_CLOSING

    @property
    def is_open(self) -> bool:
        """Return True if the cover is open."""
        state = self.get_attr(self._attribute)
        return state == STATE_OPEN or state == STATE_PARTIALLY_OPEN

    @property
    def is_opening(self) -> bool:
        """Return True if the cover is opening."""
        return self.get_attr(self._attribute) == STATE_OPENING

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._features

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this cover."""
        return f"{super().unique_id}::cover::{self._attribute}"

    @property
    def old_unique_ids(self) -> List[str]:
        """Return the legacy unique ID for this cover."""
        old_parent_ids = super().old_unique_ids
        old_ids = [f"{super().unique_id}::{self._attribute}"]
        old_ids.extend([f"{id}::{self._attribute}" for id in old_parent_ids])
        return old_ids

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        _LOGGER.debug("Closing %s", self.name)
        await self.send_command(CMD_CLOSE)

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        _LOGGER.debug("Opening %s", self.name)
        await self.send_command(CMD_OPEN)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        pos = kwargs[HA_ATTR_POSITION]
        _LOGGER.debug("Setting cover position to %s", pos)
        await self.send_command(CMD_SET_POSITION, pos)


class HubitatDoorControl(HubitatCover):
    """Representation of a Hubitat door control."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a door control."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_DOOR
        self._device_class = DEVICE_CLASS_DOOR
        self._features = SUPPORT_OPEN | SUPPORT_CLOSE


class HubitatGarageDoorControl(HubitatCover):
    """Representation of a Hubitat garage door control."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a garage door control."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_DOOR
        self._device_class = DEVICE_CLASS_GARAGE
        self._features = SUPPORT_OPEN | SUPPORT_CLOSE


class HubitatWindowShade(HubitatCover):
    """Representation of a Hubitat window shade."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a window shade."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_WINDOW_SHADE
        self._device_class = DEVICE_CLASS_SHADE
        self._features = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION


_COVER_CAPS: Tuple[Tuple[str, Type[HubitatCover]], ...] = (
    (CAP_WINDOW_SHADE, HubitatWindowShade),
    (CAP_GARAGE_DOOR_CONTROL, HubitatGarageDoorControl),
    (CAP_DOOR_CONTROL, HubitatGarageDoorControl),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: EntityAdder,
) -> None:
    """Initialize cover devices."""
    for cap in _COVER_CAPS:

        def is_cover(
            device: Device, overrides: Optional[Dict[str, str]] = None
        ) -> bool:
            return _is_cover_type(device, cap[0])

        create_and_add_entities(
            hass, entry, async_add_entities, "cover", cap[1], is_cover
        )


def is_cover(dev: Device, overrides: Optional[Dict[str, str]] = None) -> bool:
    return (
        CAP_WINDOW_SHADE in dev.capabilities
        or CAP_GARAGE_DOOR_CONTROL in dev.capabilities
        or CAP_DOOR_CONTROL in dev.capabilities
    )


def _is_cover_type(dev: Device, cap: str) -> bool:
    cover_type = None

    if CAP_WINDOW_SHADE in dev.capabilities:
        cover_type = CAP_WINDOW_SHADE
    elif CAP_GARAGE_DOOR_CONTROL in dev.capabilities:
        cover_type = CAP_GARAGE_DOOR_CONTROL
    elif CAP_DOOR_CONTROL in dev.capabilities:
        cover_type = CAP_DOOR_CONTROL

    if cover_type is None:
        return False

    return cap == cover_type
