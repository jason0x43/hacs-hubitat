"""Hubitat sensor entities."""

from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from hubitatmaker import (
    ATTR_BATTERY,
    ATTR_HUMIDITY,
    ATTR_ILLUMINANCE,
    ATTR_POWER,
    ATTR_POWER_SOURCE,
    ATTR_PRESSURE,
    ATTR_TEMPERATURE,
    ATTR_VOLTAGE,
)
from hubitatmaker.types import Device

from homeassistant.components.sensor import (
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEVICE_CLASS_TIMESTAMP,
    POWER_WATT,
    PRESSURE_MBAR,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import TEMP_F
from .device import HubitatEntity
from .entities import create_and_add_entities
from .types import EntityAdder

_LOGGER = getLogger(__name__)


class HubitatSensor(HubitatEntity):
    """A generic Hubitat sensor."""

    _attribute: str
    _units: str
    _device_class: Optional[str]

    @property
    def device_class(self) -> Optional[str]:
        """Return this sensor's device class."""
        return self._device_class

    @property
    def name(self) -> str:
        """Return this sensor's display name."""
        return f"{super().name} {self._attribute}"

    @property
    def state(self) -> Union[float, int, str, None]:
        """Return this sensor's current state."""
        return self.get_attr(self._attribute)

    @property
    def old_unique_ids(self) -> List[str]:
        """Return the legacy unique ID for this sensor."""
        old_parent_ids = super().old_unique_ids
        old_ids = [f"{super().unique_id}::{self._attribute}"]
        old_ids.extend([f"{id}::{self._attribute}" for id in old_parent_ids])
        return old_ids

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return f"{super().unique_id}::sensor::{self._attribute}"

    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the units for this sensor's value."""
        try:
            return self._units
        except AttributeError:
            return None


class HubitatBatterySensor(HubitatSensor):
    """A battery sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a battery sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_BATTERY
        self._units = "%"
        self._device_class = DEVICE_CLASS_BATTERY


class HubitatHumiditySensor(HubitatSensor):
    """A humidity sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a humidity sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_HUMIDITY
        self._units = "%"
        self._device_class = DEVICE_CLASS_HUMIDITY


class HubitatIlluminanceSensor(HubitatSensor):
    """An illuminance sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize an illuminance sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_ILLUMINANCE
        self._units = "lx"
        self._device_class = DEVICE_CLASS_ILLUMINANCE


class HubitatPowerSensor(HubitatSensor):
    """A power sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a power sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_POWER
        self._units = POWER_WATT
        self._device_class = DEVICE_CLASS_POWER


class HubitatPowerSourceSensor(HubitatSensor):
    """A power source sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a power source sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_POWER_SOURCE
        self._device_class = DEVICE_CLASS_POWER


class HubitatTemperatureSensor(HubitatSensor):
    """A temperature sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a temperature sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_TEMPERATURE
        self._device_class = DEVICE_CLASS_TEMPERATURE

    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the units for this sensor's value."""
        return TEMP_FAHRENHEIT if self._hub.temperature_unit == TEMP_F else TEMP_CELSIUS


class HubitatVoltageSensor(HubitatSensor):
    """A voltage sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a voltage sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_VOLTAGE
        self._units = "V"
        self._device_class = DEVICE_CLASS_POWER


class HubitatPressureSensor(HubitatSensor):
    """A pressure sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a pressure sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_PRESSURE

        # Maker API does not expose pressure unit
        # Override if necessary through customization.py
        # https://www.home-assistant.io/docs/configuration/customizing-devices/
        self._units = PRESSURE_MBAR

        self._device_class = DEVICE_CLASS_PRESSURE


class HubitatUpdateSensor(HubitatEntity):
    """
    A sensor that reports the last time a state update was received for a
    device.
    """

    _last_converted_update: Optional[float] = None
    _last_update_str: Optional[str] = None

    @property
    def device_class(self) -> Optional[str]:
        """Return this sensor's device class."""
        return DEVICE_CLASS_TIMESTAMP

    @property
    def name(self) -> str:
        """Return this sensor's display name."""
        return f"{super().name} last update time"

    @property
    def state(self) -> Union[float, int, str, None]:
        """Return this sensor's current state."""
        if self._last_converted_update != self.last_update:
            # Cache the converted last_update time so we're not constantly
            # doing that
            try:
                dt = datetime.fromtimestamp(self.last_update)
                self._last_update_str = dt_util.as_utc(dt).isoformat()
                self._last_converted_update = self.last_update
            except Exception as e:
                _LOGGER.warn("Error parsing last update time", e)
        return self._last_update_str

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return f"{super().unique_id}::sensor::last_update"

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Update sensors are disabled by default."""
        return False


_SENSOR_ATTRS: Tuple[Tuple[str, Type[HubitatSensor]], ...] = (
    (ATTR_BATTERY, HubitatBatterySensor),
    (ATTR_HUMIDITY, HubitatHumiditySensor),
    (ATTR_ILLUMINANCE, HubitatIlluminanceSensor),
    (ATTR_POWER, HubitatPowerSensor),
    (ATTR_POWER_SOURCE, HubitatPowerSourceSensor),
    (ATTR_PRESSURE, HubitatPressureSensor),
    (ATTR_TEMPERATURE, HubitatTemperatureSensor),
    (ATTR_VOLTAGE, HubitatVoltageSensor),
)


def is_update_sensor(
    device: Device, overrides: Optional[Dict[str, str]] = None
) -> bool:
    """Every device can have an update sensor."""
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: EntityAdder,
) -> None:
    """Initialize sensor devices."""

    # Add an update sensor for every device
    await create_and_add_entities(
        hass, entry, async_add_entities, "sensor", HubitatUpdateSensor, is_update_sensor
    )

    for attr in _SENSOR_ATTRS:

        def is_sensor(
            device: Device, overrides: Optional[Dict[str, str]] = None
        ) -> bool:
            return attr[0] in device.attributes

        await create_and_add_entities(
            hass, entry, async_add_entities, "sensor", attr[1], is_sensor
        )
