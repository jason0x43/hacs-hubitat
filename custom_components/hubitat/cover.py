from logging import getLogger
from typing import Any, Optional

from homeassistant.components.cover import (
    ATTR_POSITION as HA_ATTR_POSITION,
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_GARAGE,
    DEVICE_CLASS_SHADE,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    CoverDevice,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from hubitatmaker import (
    ATTR_DOOR,
    ATTR_POSITION,
    ATTR_WINDOW_SHADE,
    CAP_DOOR_CONTROL,
    CAP_GARAGE_DOOR_CONTROL,
    CAP_WINDOW_SHADE,
    CMD_CLOSE,
    CMD_OPEN,
    CMD_SET_POSITION,
    Device,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
)

from .device import HubitatEntity, get_hub

_LOGGER = getLogger(__name__)


class HubitatCover(HubitatEntity, CoverDevice):
    """Representation of a Hubitat cover."""

    _attribute: str
    _features: int
    _device_class: Optional[str]

    @property
    def current_cover_position(self) -> Optional[int]:
        """Return current position of cover."""
        return self.get_int_attr(ATTR_POSITION)

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
        return self.get_attr(self._attribute) == STATE_OPEN

    @property
    def is_opening(self) -> bool:
        """Return True if the cover is opening."""
        return self.get_attr(self._attribute) == STATE_OPENING

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._features

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        _LOGGER.debug("Closing %s", self.name)
        await self.send_command(CMD_CLOSE)

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        _LOGGER.debug("Opening %s", self.name)
        await self.send_command(CMD_OPEN)

    async def async_set_cover_position(self, **kwargs):
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


_COVER_CAPS = (
    (CAP_DOOR_CONTROL, HubitatDoorControl),
    (CAP_GARAGE_DOOR_CONTROL, HubitatGarageDoorControl),
    (CAP_WINDOW_SHADE, HubitatWindowShade),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities,
) -> None:
    """Initialize cover devices."""
    hub = get_hub(hass, entry.entry_id)
    devices = hub.devices

    for (cap, Cover) in _COVER_CAPS:
        covers = [
            Cover(hub=hub, device=devices[i])
            for i in devices
            if cap in devices[i].capabilities
        ]
        async_add_entities(covers)
        _LOGGER.debug(f"Added entities for covers: {covers}")
