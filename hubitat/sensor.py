"""Hubitat sensor entities."""

from logging import getLogger

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_FAHRENHEIT
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import HubitatDevice
from .hubitat import ATTR_BATTERY, ATTR_ILLUMINANCE, ATTR_TEMPERATURE, HubitatHub

_LOGGER = getLogger(__name__)


class HubitatSensor(HubitatDevice):
    """A generic Hubitat sensor."""

    @property
    def name(self):
        """Return this sensor's display name."""
        return f"{super().name} ({self._attribute})"

    @property
    def state(self):
        """Return this sensor's current state."""
        return self._get_attr(self._attribute)

    @property
    def unique_id(self):
        """Return a unique ID for this sensor."""
        return f"{super().unique_id}:{self._attribute}"

    @property
    def unit_of_measurement(self):
        """Return the units for this sensor's value."""
        try:
            return self._units
        except AttributeError:
            return None


class HubitatIlluminanceSensor(HubitatSensor):
    """An illuminance sensor."""

    def __init__(self, *args, **kwargs):
        """Initialize an illuminance sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_ILLUMINANCE
        self._units = "lx"


class HubitatTemperatureSensor(HubitatSensor):
    """A temperature sensor."""

    def __init__(self, *args, **kwargs):
        """Initialize a temperature sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_TEMPERATURE
        self._units = TEMP_FAHRENHEIT


class HubitatBatterySensor(HubitatSensor):
    """A battery sensor."""

    def __init__(self, *args, **kwargs):
        """Initialize a battery sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_BATTERY
        self._units = "%"


_SENSOR_ATTRS = (
    (ATTR_ILLUMINANCE, HubitatIlluminanceSensor),
    (ATTR_TEMPERATURE, HubitatTemperatureSensor),
    (ATTR_BATTERY, HubitatBatterySensor),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities,
):
    """Initialize light devices."""
    hub: HubitatHub = hass.data[DOMAIN][entry.entry_id].hub
    for attr in _SENSOR_ATTRS:
        Sensor = attr[1]
        sensors = [
            Sensor(hub=hub, device=d)
            for d in hub.devices
            if hub.device_has_attribute(d["id"], attr[0])
        ]
        async_add_entities(sensors)
        _LOGGER.debug(f"Added entities for sensors: {sensors}")
