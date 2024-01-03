from logging import getLogger
from typing import Any, Type, Unpack

from homeassistant.components.cover import (
    ATTR_POSITION as HA_ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .device import HubitatEntity, HubitatEntityArgs
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

    _attribute: DeviceAttribute
    _features: CoverEntityFeature

    def __init__(
        self,
        *,
        attribute: DeviceAttribute,
        features: CoverEntityFeature,
        device_class: CoverDeviceClass | None = None,
        **kwargs: Unpack[HubitatEntityArgs],
    ):
        HubitatEntity.__init__(self, device_class=device_class, **kwargs)
        CoverEntity.__init__(self)

        self._attribute = attribute
        self._attr_supported_features = features
        self._attr_unique_id = f"{super().unique_id}::cover::{attribute}"

    @property
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return (
            self._attribute,
            DeviceAttribute.LEVEL,
            DeviceAttribute.POSITION,
        )

    @property
    def name(self) -> str:
        """Return the display name for this select."""
        return f"{super().name} {self._attribute}".title()

    @property
    def current_cover_position(self) -> int | None:
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
        """Return True if the cover is closing."""
        return self.get_attr(self._attribute) == DeviceState.CLOSING

    @property
    def is_opening(self) -> bool:
        """Return True if the cover is opening."""
        state = self.get_attr(self._attribute)
        return state == DeviceState.OPENING

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

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a door control."""
        super().__init__(
            attribute=DeviceAttribute.DOOR,
            features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
            device_class=CoverDeviceClass.DOOR,
            **kwargs,
        )


class HubitatGarageDoorControl(HubitatCover):
    """Representation of a Hubitat garage door control."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a garage door control."""
        super().__init__(
            attribute=DeviceAttribute.DOOR,
            features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
            device_class=CoverDeviceClass.GARAGE,
            **kwargs,
        )


class HubitatWindowShade(HubitatCover):
    """Representation of a Hubitat window shade."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a window shade."""
        super().__init__(
            attribute=DeviceAttribute.WINDOW_SHADE,
            features=(
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.SET_POSITION
            ),
            device_class=CoverDeviceClass.SHADE,
            **kwargs,
        )


class HubitatWindowBlind(HubitatCover):
    """Representation of a Hubitat window blind."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a window blind."""
        super().__init__(
            attribute=DeviceAttribute.WINDOW_BLIND,
            features=(
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.SET_POSITION
            ),
            device_class=CoverDeviceClass.BLIND,
            **kwargs,
        )


class HubitatWindowControl(HubitatCover):
    """Representation of a Hubitat window control."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a window control."""
        super().__init__(
            attribute=DeviceAttribute.WINDOW_SHADE,
            features=(
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.SET_POSITION
            ),
            device_class=CoverDeviceClass.WINDOW,
            **kwargs,
        )


_COVER_CAPS: tuple[tuple[DeviceCapability, Type[HubitatCover]], ...] = (
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

        def is_cover(device: Device, overrides: dict[str, str] | None = None) -> bool:
            return _is_cover_type(device, cap[0])

        create_and_add_entities(
            hass, entry, async_add_entities, "cover", cap[1], is_cover
        )


def is_cover(dev: Device, overrides: dict[str, str] | None = None) -> bool:
    return (
        DeviceCapability.WINDOW_SHADE in dev.capabilities
        or DeviceCapability.WINDOW_BLIND in dev.capabilities
        or DeviceCapability.GARAGE_DOOR_CONTROL in dev.capabilities
        or DeviceCapability.DOOR_CONTROL in dev.capabilities
    )


def _is_cover_type(dev: Device, cap: DeviceCapability) -> bool:
    cover_type: DeviceCapability | None = None

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
