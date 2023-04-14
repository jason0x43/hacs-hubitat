"""Hubitat sensor entities."""

from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union

from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    CURRENCY_EURO,
    DEGREE,
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolume,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_HSM_STATUS,
    ATTR_MODE,
    TEMP_F,
    DeviceType,
)
from .device import HubitatEntity
from .entities import create_and_add_entities
from .hub import get_hub
from .hubitatmaker import DeviceAttribute
from .hubitatmaker.types import Device
from .types import EntityAdder

_LOGGER = getLogger(__name__)


class HubitatSensor(HubitatEntity):
    """A generic Hubitat sensor."""

    _attribute: str
    _attribute_name: Optional[str] = None
    _units: str | None
    _device_class: Optional[str] = None
    _state_class: Optional[str] = None
    _enabled_default: Optional[bool] = None

    def __init__(
        self,
        *args: Any,
        attribute: Optional[str] = None,
        attribute_name: Optional[str] = None,
        units: Optional[str] = None,
        device_class: Optional[str] = None,
        state_class: Optional[str] = None,
        enabled_default: Optional[bool] = None,
        **kwargs: Any,
    ):
        """Initialize a battery sensor."""
        super().__init__(*args, **kwargs)

        if attribute is not None:
            self._attribute = attribute
        if attribute_name is not None:
            self._attribute_name = attribute_name
        if units is not None:
            self._units = units
        if device_class is not None:
            self._device_class = device_class
        if state_class is not None:
            self._state_class = state_class
        if enabled_default is not None:
            self._enabled_default = enabled_default

    @property
    def device_attrs(self) -> Optional[Sequence[str]]:
        """Return this entity's associated attributes"""
        return (self._attribute,)

    @property
    def device_class(self) -> Optional[str]:
        """Return this sensor's device class."""
        return self._device_class

    @property
    def state_class(self) -> Optional[str]:
        """Return this sensor's state class."""
        return self._state_class

    @property
    def name(self) -> str:
        """Return this sensor's display name."""
        attr_name = getattr(self, "_attribute_name", None) or self._attribute.replace(
            "_", " "
        )
        return f"{super().name} {attr_name}".title()

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

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Update sensors are disabled by default."""
        if self._enabled_default is not None:
            return self._enabled_default
        return True


class HubitatBatterySensor(HubitatSensor):
    """A battery sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a battery sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.BATTERY
        self._units = PERCENTAGE
        self._device_class = SensorDeviceClass.BATTERY
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatEnergySensor(HubitatSensor):
    """A energy sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a energy sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.ENERGY
        self._units = UnitOfEnergy.KILO_WATT_HOUR
        self._device_class = SensorDeviceClass.ENERGY
        self._state_class = SensorStateClass.TOTAL


class HubitatEnergySourceSensor(HubitatSensor):
    """A energy source sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a energy source sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.ENERGY_SOURCE
        self._device_class = None
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatHumiditySensor(HubitatSensor):
    """A humidity sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a humidity sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.HUMIDITY
        self._units = PERCENTAGE
        self._device_class = SensorDeviceClass.HUMIDITY
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatIlluminanceSensor(HubitatSensor):
    """An illuminance sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize an illuminance sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.ILLUMINANCE
        self._units = LIGHT_LUX
        self._device_class = SensorDeviceClass.ILLUMINANCE
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatPowerSensor(HubitatSensor):
    """A power sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a power sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.POWER
        self._units = UnitOfPower.WATT
        self._device_class = SensorDeviceClass.POWER
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatPowerSourceSensor(HubitatSensor):
    """A power source sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a power source sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.POWER_SOURCE
        self._device_class = SensorDeviceClass.POWER


class HubitatTemperatureSensor(HubitatSensor):
    """A temperature sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a temperature sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.TEMPERATURE
        self._device_class = SensorDeviceClass.TEMPERATURE
        self._state_class = SensorStateClass.MEASUREMENT

    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the units for this sensor's value."""
        return (
            UnitOfTemperature.FAHRENHEIT
            if self._hub.temperature_unit == TEMP_F
            else UnitOfTemperature.CELSIUS
        )


class HubitatDewPointSensor(HubitatSensor):
    """A dewpoint sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a dewpoint sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.DEW_POINT
        self._device_class = SensorDeviceClass.TEMPERATURE
        self._state_class = SensorStateClass.MEASUREMENT

    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the units for this sensor's value."""
        return (
            UnitOfTemperature.FAHRENHEIT
            if self._hub.temperature_unit == TEMP_F
            else UnitOfTemperature.CELSIUS
        )


class HubitatVoltageSensor(HubitatSensor):
    """A voltage sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a voltage sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.VOLTAGE
        self._units = UnitOfElectricPotential.VOLT
        self._device_class = SensorDeviceClass.VOLTAGE
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatPressureSensor(HubitatSensor):
    """A pressure sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a pressure sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.PRESSURE

        # Maker API does not expose pressure unit
        # Override if necessary through customization.py
        # https://www.home-assistant.io/docs/configuration/customizing-devices/
        self._units = UnitOfPressure.MBAR
        self._device_class = SensorDeviceClass.PRESSURE
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatCarbonDioxide(HubitatSensor):
    """A CarbonDioxide sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a CarbonDioxide sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.CARBON_DIOXIDE
        self._units = CONCENTRATION_PARTS_PER_MILLION
        self._device_class = SensorDeviceClass.CO2
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatCarbonDioxideLevel(HubitatSensor):
    """A CarbonDioxideLevel sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a CarbonDioxideLevel sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.CARBON_DIOXIDE_LEVEL
        self._units = None
        self._device_class = SensorDeviceClass.CO2
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatCarbonMonoxide(HubitatSensor):
    """A CarbonMonoxide sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a CarbonMonoxide sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.CARBON_MONOXIDE
        self._units = CONCENTRATION_PARTS_PER_MILLION
        self._device_class = SensorDeviceClass.CO
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatCarbonMonoxideLevel(HubitatSensor):
    """A CarbonMonoxideLevel sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a CarbonMonoxideLevel sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.CARBON_MONOXIDE_LEVEL
        self._units = None
        self._device_class = SensorDeviceClass.CO
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatVOC(HubitatSensor):
    """A VOC sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a VOC sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.VOC
        self._units = CONCENTRATION_PARTS_PER_BILLION
        self._device_class = SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatVOCLevel(HubitatSensor):
    """A VOC-Level sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a VOC-Level sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.VOC_LEVEL
        self._units = None
        self._device_class = SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatHomeHealth(HubitatSensor):
    """A HomeHealth sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a HomeHealth sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.HOME_HEALTH
        self._units = None
        self._device_class = None
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatCurrentSensor(HubitatSensor):
    """A current sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a current sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.AMPERAGE
        self._units = UnitOfElectricCurrent.AMPERE
        self._device_class = SensorDeviceClass.CURRENT
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatUVIndexSensor(HubitatSensor):
    """A UV index sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a UV index sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.UV
        self._device_class = None
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatAqiSensor(HubitatSensor):
    """An AQI sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize an AQI sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.AQI
        self._units = "AQI"
        self._device_class = SensorDeviceClass.AQI
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatAirQualityIndexSensor(HubitatSensor):
    """An airQualityIndex sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize an airQualityIndex sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.AIR_QUALITY_INDEX
        self._units = "AQI"
        self._device_class = SensorDeviceClass.AQI
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatPm1Sensor(HubitatSensor):
    """A PM1 sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a PM1 sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.PM1
        self._units = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
        self._device_class = SensorDeviceClass.PM1
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatPm10Sensor(HubitatSensor):
    """A PM10 sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a PM10 sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.PM10
        self._units = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
        self._device_class = SensorDeviceClass.PM10
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatPm25Sensor(HubitatSensor):
    """A PM2.5 sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a PM2.5 sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.PM25
        self._units = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
        self._device_class = SensorDeviceClass.PM25
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatRainRateSensor(HubitatSensor):
    """A rain rate sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a rain rate sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.RAIN_RATE
        self._units = UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR
        self._device_class = SensorDeviceClass.PRECIPITATION_INTENSITY
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatRainDailySensor(HubitatSensor):
    """A rain daily sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a rain daily sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.RAIN_DAILY
        self._units = UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR
        self._device_class = SensorDeviceClass.PRECIPITATION_INTENSITY
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatWindDirectionSensor(HubitatSensor):
    """A wind direction sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a wind direction sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.WIND_DIRECTION
        self._units = DEGREE
        self._device_class = SensorDeviceClass.WIND_SPEED
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatWindSpeedSensor(HubitatSensor):
    """A wind speed sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a wind speed sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.WIND_SPEED
        self._units = UnitOfSpeed.KILOMETERS_PER_HOUR
        self._device_class = SensorDeviceClass.WIND_SPEED
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatWindGustSensor(HubitatSensor):
    """A wind gust sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a wind gust sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.WIND_GUST
        self._units = UnitOfSpeed.KILOMETERS_PER_HOUR
        self._device_class = SensorDeviceClass.WIND_SPEED
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatRateSensor(HubitatSensor):
    """A rate sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a rate sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.RATE
        self._units = None
        self._device_class = None
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatWaterDayPriceSensor(HubitatSensor):
    """A water day liter price sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a water day liter price sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.DAY_EURO
        self._units = CURRENCY_EURO
        self._device_class = NumberDeviceClass.MONETARY
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatWaterDayLiterSensor(HubitatSensor):
    """A water day liter sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a water day liter sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.DAY_LITER
        self._units = UnitOfVolume.LITERS
        self._device_class = SensorDeviceClass.WATER
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatWaterCumulativeLiterSensor(HubitatSensor):
    """A water cumulative liter sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a water cumulative liter sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.CUMULATIVE_LITER
        self._units = UnitOfVolume.LITERS
        self._device_class = SensorDeviceClass.WATER
        self._state_class = SensorStateClass.TOTAL_INCREASING


class HubitatWaterCumulativeM3Sensor(HubitatSensor):
    """A water cumulative m3 sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a water cumulative m3 sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.CUMULATIVE_CUBIC_METER
        self._units = UnitOfVolume.CUBIC_METERS
        self._device_class = SensorDeviceClass.WATER
        self._state_class = SensorStateClass.MEASUREMENT


class HubitatWaterDayM3Sensor(HubitatSensor):
    """A water day m3 sensor."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize a water day m3 sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = DeviceAttribute.DAY_CUBIC_METER
        self._units = UnitOfVolume.CUBIC_METERS
        self._device_class = SensorDeviceClass.WATER
        self._state_class = SensorStateClass.MEASUREMENT


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
        return SensorDeviceClass.TIMESTAMP

    @property
    def name(self) -> str:
        """Return this sensor's display name."""
        return f"{super().name.title()} Last Update Time"

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


class HubitatHsmSensor(HubitatSensor):
    """
    A sensor that reports a hub's HSM status.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize an hsm status sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_HSM_STATUS
        self._device_class = DeviceType.HUB_HSM_STATUS
        self._attribute_name = "HSM status"


class HubitatHubModeSensor(HubitatSensor):
    """
    A sensor that reports a hub's mode.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize an hsm status sensor."""
        super().__init__(*args, **kwargs)
        self._attribute = ATTR_MODE
        self._device_class = DeviceType.HUB_MODE


_SENSOR_ATTRS: Tuple[Tuple[str, Type[HubitatSensor]], ...] = (
    (DeviceAttribute.AIR_QUALITY_INDEX, HubitatAirQualityIndexSensor),
    (DeviceAttribute.AMPERAGE, HubitatCurrentSensor),
    (DeviceAttribute.AQI, HubitatAqiSensor),
    (DeviceAttribute.BATTERY, HubitatBatterySensor),
    (DeviceAttribute.CARBON_DIOXIDE, HubitatCarbonDioxide),
    (DeviceAttribute.CARBON_DIOXIDE_LEVEL, HubitatCarbonDioxideLevel),
    (DeviceAttribute.CARBON_MONOXIDE, HubitatCarbonMonoxide),
    (DeviceAttribute.CARBON_MONOXIDE_LEVEL, HubitatCarbonMonoxideLevel),
    (DeviceAttribute.CUMULATIVE_CUBIC_METER, HubitatWaterCumulativeM3Sensor),
    (DeviceAttribute.CUMULATIVE_LITER, HubitatWaterCumulativeLiterSensor),
    (DeviceAttribute.DAY_CUBIC_METER, HubitatWaterDayM3Sensor),
    (DeviceAttribute.DAY_EURO, HubitatWaterDayPriceSensor),
    (DeviceAttribute.DAY_LITER, HubitatWaterDayLiterSensor),
    (DeviceAttribute.DEW_POINT, HubitatDewPointSensor),
    (DeviceAttribute.ENERGY, HubitatEnergySensor),
    (DeviceAttribute.ENERGY_SOURCE, HubitatEnergySourceSensor),
    (DeviceAttribute.HOME_HEALTH, HubitatHomeHealth),
    (DeviceAttribute.HUMIDITY, HubitatHumiditySensor),
    (DeviceAttribute.ILLUMINANCE, HubitatIlluminanceSensor),
    (DeviceAttribute.PM1, HubitatPm1Sensor),
    (DeviceAttribute.PM10, HubitatPm10Sensor),
    (DeviceAttribute.PM25, HubitatPm25Sensor),
    (DeviceAttribute.POWER, HubitatPowerSensor),
    (DeviceAttribute.POWER_SOURCE, HubitatPowerSourceSensor),
    (DeviceAttribute.PRESSURE, HubitatPressureSensor),
    (DeviceAttribute.RAIN_DAILY, HubitatRainDailySensor),
    (DeviceAttribute.RAIN_RATE, HubitatRainRateSensor),
    (DeviceAttribute.RATE, HubitatRateSensor),
    (DeviceAttribute.TEMPERATURE, HubitatTemperatureSensor),
    (DeviceAttribute.UV, HubitatUVIndexSensor),
    (DeviceAttribute.VOC, HubitatVOC),
    (DeviceAttribute.VOC_LEVEL, HubitatVOCLevel),
    (DeviceAttribute.VOLTAGE, HubitatVoltageSensor),
    (DeviceAttribute.WIND_DIRECTION, HubitatWindDirectionSensor),
    (DeviceAttribute.WIND_GUST, HubitatWindGustSensor),
    (DeviceAttribute.WIND_SPEED, HubitatWindSpeedSensor),
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

    add_hub_entities(hass, entry, async_add_entities)

    # Add an update sensor for every device
    create_and_add_entities(
        hass, entry, async_add_entities, "sensor", HubitatUpdateSensor, is_update_sensor
    )

    for attr in _SENSOR_ATTRS:

        def is_sensor(
            device: Device, overrides: Optional[Dict[str, str]] = None
        ) -> bool:
            return attr[0] in device.attributes

        create_and_add_entities(
            hass, entry, async_add_entities, "sensor", attr[1], is_sensor
        )

    # Create sensor entities for any attributes that don't correspond to known
    # sensor types
    unknown_entities: List[HubitatEntity] = []
    hub = get_hub(hass, entry.entry_id)

    for id in hub.devices:
        device = hub.devices[id]
        device_entities = [e for e in hub.entities if e.device_id == id]
        used_device_attrs: set[str] = set()
        for entity in device_entities:
            if entity.device_attrs is not None:
                for attr in entity.device_attrs:
                    used_device_attrs.add(attr)
        for attr in device.attributes:
            if attr not in used_device_attrs:
                unknown_entities.append(
                    HubitatSensor(
                        hub=hub,
                        device=device,
                        attribute=attr,
                        enabled_default=False,
                        device_class="unknown",
                    )
                )
                _LOGGER.debug(f"Adding unknown entity for {device.id}:{attr}")

    if len(unknown_entities) > 0:
        hub.add_entities(unknown_entities)
        async_add_entities(unknown_entities)


def add_hub_entities(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: EntityAdder
) -> None:
    """Add entities for hub services."""

    hub_entities = []
    hub = get_hub(hass, entry.entry_id)

    if hub.hsm_supported:
        hub_entities.append(HubitatHsmSensor(hub=hub, device=hub.device))

    if hub.mode_supported:
        hub_entities.append(HubitatHubModeSensor(hub=hub, device=hub.device))

    if len(hub_entities) > 0:
        hub.add_entities(hub_entities)
        async_add_entities(hub_entities)
