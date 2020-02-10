"""Hubitat sensor entities."""

from logging import getLogger
from typing import Any, Optional, Union

from hubitatmaker import (
    ATTR_BATTERY,
    ATTR_CURRENT,
    ATTR_HUMIDITY,
    ATTR_ILLUMINANCE,
    ATTR_POWER,
    ATTR_TEMPERATURE,
    ATTR_VOLTAGE,
    Hub,
)

from homeassistant.components.sensor import (
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_TEMPERATURE,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import POWER_WATT, TEMP_FAHRENHEIT
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import HubitatStatefulDevice

_LOGGER = getLogger(__name__)


class HubitatSensor(HubitatStatefulDevice):
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
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return f"{super().unique_id}::{self._attribute}"

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


class HubitatTemperatureSensor(HubitatSensor):
    """A temperature sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a temperature sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_TEMPERATURE
        self._units = TEMP_FAHRENHEIT
        self._device_class = DEVICE_CLASS_TEMPERATURE


class HubitatVoltageSensor(HubitatSensor):
    """A voltage sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a voltage sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_VOLTAGE
        self._units = "V"
        self._device_class = DEVICE_CLASS_POWER


_SENSOR_ATTRS = (
    (ATTR_BATTERY, HubitatBatterySensor),
    (ATTR_HUMIDITY, HubitatHumiditySensor),
    (ATTR_ILLUMINANCE, HubitatIlluminanceSensor),
    (ATTR_POWER, HubitatPowerSensor),
    (ATTR_TEMPERATURE, HubitatTemperatureSensor),
    (ATTR_VOLTAGE, HubitatVoltageSensor),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities,
) -> None:
    """Initialize sensor devices."""
    hub: Hub = hass.data[DOMAIN][entry.entry_id].hub
    devices = hub.devices
    for attr in _SENSOR_ATTRS:
        Sensor = attr[1]
        sensors = [
            Sensor(hub=hub, device=devices[i])
            for i in devices
            if attr[0] in devices[i].attributes
        ]
        async_add_entities(sensors)
        _LOGGER.debug(f"Added entities for sensors: {sensors}")
