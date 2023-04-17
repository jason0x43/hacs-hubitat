from logging import getLogger
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type

from homeassistant.components.cover import (
    ATTR_POSITION as HA_ATTR_POSITION,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    CoverDeviceClass,
    CoverEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .device import HubitatEntity
from .entities import create_and_add_entities
from .hubitatmaker import (
    Device,
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
    DeviceState,
)
from .types import EntityAdder

_LOGGER = getLogger(__name__)


class HubitatCover(HubitatEntity, CoverEntity):
    """Representation of a Hubitat cover."""

    _attribute: str
    _features: int
    _device_class: Optional[str]

    @property
    def device_attrs(self) -> Optional[Sequence[str]]:
        """Return this entity's associated attributes"""
        return (
            self._attribute,
            DeviceAttribute.LEVEL,
            DeviceAttribute.POSITION,
        )

    @property
    def device_class(self) -> Optional[str]:
        """Return this sensor's device class."""
        return self._device_class

    @property
    def current_cover_position(self) -> Optional[int]:
        """Return current position of cover."""
        pos = self.get_int_attr(DeviceAttribute.POSITION)
        if pos is not None:
            return pos
        # At least the Qubino Roller Shutter driver reports the shade position
        # using the 'level' parameter
        return self.get_int_attr(DeviceAttribute.LEVEL)

    @property
    def is_closed(self) -> bool:
        """Return True if the cover is closed."""
        return self.get_attr(self._attribute) == DeviceState.CLOSED

    @property
    def is_closing(self) -> bool:
        """Return True if the cover is opening."""
        return self.get_attr(self._attribute) == DeviceState.CLOSING

    @property
    def is_open(self) -> bool:
        """Return True if the cover is open."""
        state = self.get_attr(self._attribute)
        return state == DeviceState.OPEN or state == DeviceState.PARTIALLY_OPEN

    @property
    def is_opening(self) -> bool:
        """Return True if the cover is opening."""
        return self.get_attr(self._attribute) == DeviceState.OPENING

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
        await self.send_command(DeviceCommand.CLOSE)

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        _LOGGER.debug("Opening %s", self.name)
        await self.send_command(DeviceCommand.OPEN)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        pos = kwargs[HA_ATTR_POSITION]
        _LOGGER.debug("Setting cover position to %s", pos)
        await self.send_command(DeviceCommand.SET_POSITION, pos)


class HubitatDoorControl(HubitatCover):
    """Representation of a Hubitat door control."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a door control."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.DOOR
        self._device_class = CoverDeviceClass.DOOR
        self._features = SUPPORT_OPEN | SUPPORT_CLOSE


class HubitatGarageDoorControl(HubitatCover):
    """Representation of a Hubitat garage door control."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a garage door control."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.DOOR
        self._device_class = CoverDeviceClass.GARAGE
        self._features = SUPPORT_OPEN | SUPPORT_CLOSE


class HubitatWindowShade(HubitatCover):
    """Representation of a Hubitat window shade."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a window shade."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.WINDOW_SHADE
        self._device_class = CoverDeviceClass.SHADE
        self._features = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION


class HubitatWindowBlind(HubitatCover):
    """Representation of a Hubitat window blind."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a window blind."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.WINDOW_BLIND
        self._device_class = CoverDeviceClass.BLIND
        self._features = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION


class HubitatWindowControl(HubitatCover):
    """Representation of a Hubitat window control."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a window control."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.WINDOW_SHADE
        self._device_class = CoverDeviceClass.WINDOW
        self._features = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION


_COVER_CAPS: Tuple[Tuple[str, Type[HubitatCover]], ...] = (
    (DeviceCapability.DOOR_CONTROL, HubitatGarageDoorControl),
    (DeviceCapability.GARAGE_DOOR_CONTROL, HubitatGarageDoorControl),
    (DeviceCapability.WINDOW_BLIND, HubitatWindowBlind),
    (DeviceCapability.WINDOW_SHADE, HubitatWindowShade),
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
        DeviceCapability.WINDOW_SHADE in dev.capabilities
        or DeviceCapability.WINDOW_BLIND in dev.capabilities
        or DeviceCapability.GARAGE_DOOR_CONTROL in dev.capabilities
        or DeviceCapability.DOOR_CONTROL in dev.capabilities
    )


def _is_cover_type(dev: Device, cap: str) -> bool:
    cover_type = None

    if DeviceCapability.WINDOW_SHADE in dev.capabilities:
        cover_type = DeviceCapability.WINDOW_SHADE
    elif DeviceCapability.WINDOW_BLIND in dev.capabilities:
        cover_type = DeviceCapability.WINDOW_BLIND
    elif DeviceCapability.GARAGE_DOOR_CONTROL in dev.capabilities:
        cover_type = DeviceCapability.GARAGE_DOOR_CONTROL
    elif DeviceCapability.DOOR_CONTROL in dev.capabilities:
        cover_type = DeviceCapability.DOOR_CONTROL

    if cover_type is None:
        return False

    return cap == cover_type
