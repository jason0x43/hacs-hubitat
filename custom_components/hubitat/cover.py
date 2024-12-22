from logging import getLogger
from typing import TYPE_CHECKING, Any, Unpack, cast, override

from homeassistant.components.cover import (
    ATTR_POSITION as HA_ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device import HubitatEntity, HubitatEntityArgs
from .entities import create_and_add_entities
from .hubitatmaker import (
    Device,
    DeviceAttribute,
    DeviceCapability,
    DeviceCommand,
    DeviceState,
)

_LOGGER = getLogger(__name__)


class HubitatCover(HubitatEntity, CoverEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
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
        self._attr_supported_features: CoverEntityFeature | None = features  # pyright: ignore[reportIncompatibleVariableOverride]
        self._attr_unique_id: str | None = f"{super().unique_id}::cover::{attribute}"
        self._attr_name: str | None = f"{super().name} {self._attribute}".title()
        self._device_attrs: tuple[DeviceAttribute, ...] = (
            self._attribute,
            DeviceAttribute.LEVEL,
            DeviceAttribute.POSITION,
        )

        self.load_state()

    @override
    def load_state(self):
        self._attr_current_cover_position: int | None = (
            self._get_current_cover_position()
        )
        self._attr_is_closed: bool | None = self._get_is_closed()
        self._attr_is_closing: bool | None = self._get_is_closing()
        self._attr_is_opening: bool | None = self._get_is_opening()

    def _get_current_cover_position(self) -> int | None:
        pos = self.get_int_attr(DeviceAttribute.POSITION)
        if pos is not None:
            return pos
        # At least the Qubino Roller Shutter driver reports the shade position
        # using the 'level' parameter
        return self.get_int_attr(DeviceAttribute.LEVEL)

    def _get_is_closed(self) -> bool:
        return self.get_attr(self._attribute) == DeviceState.CLOSED

    def _get_is_closing(self) -> bool:
        return self.get_attr(self._attribute) == DeviceState.CLOSING

    def _get_is_opening(self) -> bool:
        return self.get_attr(self._attribute) == DeviceState.OPENING

    @property
    @override
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return self._device_attrs

    @override
    async def async_close_cover(self, **kwargs: Any) -> None:  # pyright: ignore[reportAny]
        """Close the cover."""
        _LOGGER.debug("Closing %s", self.name)
        await self.send_command(DeviceCommand.CLOSE)

    @override
    async def async_open_cover(self, **kwargs: Any) -> None:  # pyright: ignore[reportAny]
        """Open the cover."""
        _LOGGER.debug("Opening %s", self.name)
        await self.send_command(DeviceCommand.OPEN)

    @override
    async def async_set_cover_position(self, **kwargs: Any) -> None:  # pyright: ignore[reportAny]
        """Move the cover to a specific position."""
        pos = cast(str, kwargs[HA_ATTR_POSITION])
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


_COVER_CAPS: tuple[tuple[DeviceCapability, type[HubitatCover]], ...] = (
    (DeviceCapability.DOOR_CONTROL, HubitatGarageDoorControl),
    (DeviceCapability.GARAGE_DOOR_CONTROL, HubitatGarageDoorControl),
    (DeviceCapability.WINDOW_BLIND, HubitatWindowBlind),
    (DeviceCapability.WINDOW_SHADE, HubitatWindowShade),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize cover devices."""
    for cap in _COVER_CAPS:

        def is_cover(device: Device, _overrides: dict[str, str] | None = None) -> bool:
            return _is_cover_type(device, cap[0])

        _ = create_and_add_entities(
            hass, entry, async_add_entities, "cover", cap[1], is_cover
        )


def is_cover(dev: Device, _overrides: dict[str, str] | None = None) -> bool:
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


if TYPE_CHECKING:
    from .hub import DEVICE_TYPECHECK, HUB_TYPECHECK

    test_alarm = HubitatCover(
        hub=HUB_TYPECHECK,
        device=DEVICE_TYPECHECK,
        attribute=DeviceAttribute.DOOR,
        features=(CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE),
    )
