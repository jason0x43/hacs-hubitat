"""Hubitat sensor entities."""

import re
from datetime import date, datetime
from decimal import Decimal
from logging import getLogger
from typing import TYPE_CHECKING, Unpack, override

from custom_components.hubitat.hubitatmaker.const import DeviceCapability
from custom_components.hubitat.util import to_display_name
from homeassistant.components.sensor import (
    SensorEntity,
)
from homeassistant.components.sensor.const import (
    SensorDeviceClass,
    SensorStateClass,
)
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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .device import HubitatEntity, HubitatEntityArgs
from .entities import create_and_add_entities
from .hub import get_hub
from .hubitatmaker import DeviceAttribute
from .hubitatmaker.types import Device

_LOGGER = getLogger(__name__)

PRESSURE_UNITS: dict[str, UnitOfPressure] = {
    "pa": UnitOfPressure.PA,
    "hpa": UnitOfPressure.HPA,
    "kpa": UnitOfPressure.KPA,
    "bar": UnitOfPressure.BAR,
    "cbar": UnitOfPressure.CBAR,
    "mbar": UnitOfPressure.MBAR,
    "mmhg": UnitOfPressure.MMHG,
    "inhg": UnitOfPressure.INHG,
    "psi": UnitOfPressure.PSI,
}


class HubitatSensor(HubitatEntity, SensorEntity):
    """A generic Hubitat sensor."""

    _attribute: DeviceAttribute
    _enabled_default: bool | None = None

    def __init__(
        self,
        *,
        attribute: DeviceAttribute,
        attribute_name: str | None = None,
        unit: str | None = None,
        device_class: SensorDeviceClass | None = None,
        state_class: SensorStateClass | None = None,
        enabled_default: bool | None = None,
        # TODO: load options from device
        options: list[str] | None = None,
        **kwargs: Unpack[HubitatEntityArgs],
    ):
        """Initialize a battery sensor."""
        HubitatEntity.__init__(self, **kwargs)
        SensorEntity.__init__(self)

        attr_name = (
            attribute_name
            if attribute_name is not None
            else attribute.replace("_", " ")
        )

        self._attribute = attribute
        self._attr_name: str | None = (
            f"{super(HubitatEntity, self).name} {attr_name}".title()
        )
        self._attr_native_unit_of_measurement: str | None = unit
        self._attr_device_class: SensorDeviceClass | None = device_class  # pyright: ignore[reportIncompatibleVariableOverride]
        self._attr_state_class: SensorStateClass | str | None = state_class
        self._attr_unique_id: str | None = f"{super().unique_id}::sensor::{attribute}"
        self._attr_entity_registry_enabled_default: bool = (
            enabled_default if enabled_default is not None else True
        )

        if options is not None:
            self._attr_options: list[str] | None = options

        self.load_state()

    @override
    def load_state(self):
        self._attr_native_value: StateType | date | datetime | Decimal = (
            self._get_native_value()
        )

    @property
    @override
    def device_attrs(self) -> tuple[DeviceAttribute, ...] | None:
        """Return this entity's associated attributes"""
        return (self._attribute,)

    def _get_native_value(self) -> StateType | date | datetime | Decimal:
        """Return this sensor's current value."""
        return self.get_attr(self._attribute)


class HubitatBatterySensor(HubitatSensor):
    """A battery sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a battery sensor."""
        super().__init__(
            attribute=DeviceAttribute.BATTERY,
            unit=PERCENTAGE,
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )

    @override
    def load_state(self):
        super().load_state()
        self._attr_native_value: StateType | date | datetime | Decimal = (
            self._get_native_value()
        )

    @override
    def _get_native_value(self) -> StateType | date | datetime | Decimal:
        """Return this battery sensor's current value."""
        value = self.get_attr(self._attribute)
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                # Some devices don't follow the spec
                # See https://github.com/jason0x43/hacs-hubitat/issues/252#issuecomment-1896327401
                match = re.match(r"Battery (\d.*)%", value)
                if match:
                    value = float(match.group(1))
        return value


class HubitatEnergySensor(HubitatSensor):
    """A energy sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a energy sensor."""
        super().__init__(
            attribute=DeviceAttribute.ENERGY,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL,
            **kwargs,
        )


class HubitatEnergySourceSensor(HubitatSensor):
    """A energy source sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a energy source sensor."""
        super().__init__(
            attribute=DeviceAttribute.ENERGY_SOURCE,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatHumiditySensor(HubitatSensor):
    """A humidity sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a humidity sensor."""
        super().__init__(
            attribute=DeviceAttribute.HUMIDITY,
            unit=PERCENTAGE,
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatIlluminanceSensor(HubitatSensor):
    """An illuminance sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize an illuminance sensor."""
        super().__init__(
            attribute=DeviceAttribute.ILLUMINANCE,
            unit=LIGHT_LUX,
            device_class=SensorDeviceClass.ILLUMINANCE,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatPowerSensor(HubitatSensor):
    """A power sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a power sensor."""
        super().__init__(
            attribute=DeviceAttribute.POWER,
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatPowerSourceSensor(HubitatSensor):
    """A power source sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a power source sensor."""
        super().__init__(
            attribute=DeviceAttribute.POWER_SOURCE,
            device_class=SensorDeviceClass.ENUM,
            **kwargs,
        )


class HubitatTemperatureSensor(HubitatSensor):
    """A temperature sensor."""

    def __init__(
        self,
        attribute: DeviceAttribute = DeviceAttribute.TEMPERATURE,
        **kwargs: Unpack[HubitatEntityArgs],
    ):
        """Initialize a temperature sensor."""
        super().__init__(
            attribute=attribute,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )

    @override
    def load_state(self):
        super().load_state()
        self._attr_native_unit_of_measurement: str | None = (
            self._get_native_unit_of_measurement()
        )

    def _get_native_unit_of_measurement(self) -> str | None:
        unit: UnitOfTemperature = self._hub.temperature_unit
        attr_unit: str | None = self.get_attr_unit(self._attribute)
        if attr_unit is not None:
            if "F" in attr_unit:
                return UnitOfTemperature.FAHRENHEIT
            return UnitOfTemperature.CELSIUS
        return unit


class HubitatDewPointSensor(HubitatTemperatureSensor):
    """A dewpoint sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a dewpoint sensor."""
        super().__init__(attribute=DeviceAttribute.DEW_POINT, **kwargs)


class HubitatVoltageSensor(HubitatSensor):
    """A voltage sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a voltage sensor."""
        super().__init__(
            attribute=DeviceAttribute.VOLTAGE,
            unit=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatPressureSensor(HubitatSensor):
    """A pressure sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a pressure sensor."""
        # Maker API does not expose pressure unit
        # Override if necessary through customization.py
        # https://www.home-assistant.io/docs/configuration/customizing-devices/
        super().__init__(
            attribute=DeviceAttribute.PRESSURE,
            unit=UnitOfPressure.MBAR,
            device_class=SensorDeviceClass.PRESSURE,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )

    @override
    def load_state(self):
        super().load_state()
        self._attr_native_unit_of_measurement: str | None = (
            self._get_native_unit_of_measurement()
        )

    def _get_native_unit_of_measurement(self) -> str | None:
        """Return this sensor's current value."""
        attr_unit = self.get_attr_unit(self._attribute)
        if attr_unit is not None:
            lower_unit = attr_unit.lower()
            if lower_unit in PRESSURE_UNITS:
                _LOGGER.debug(f"Using Hubitat unit {attr_unit} for {self.unique_id}")
                return PRESSURE_UNITS[lower_unit]
        _LOGGER.debug(f"Using default unit mbar for {self.unique_id}")
        return UnitOfPressure.MBAR


class HubitatCarbonDioxide(HubitatSensor):
    """A CarbonDioxide sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a CarbonDioxide sensor."""
        super().__init__(
            attribute=DeviceAttribute.CARBON_DIOXIDE,
            unit=CONCENTRATION_PARTS_PER_MILLION,
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


# This attribute isn't from the Hubitat spec, but appears to be an air quality
# enumeration. See https://github.com/jason0x43/hacs-hubitat/issues/117
class HubitatCarbonDioxideLevel(HubitatSensor):
    """A CarbonDioxideLevel sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a CarbonDioxideLevel sensor."""
        super().__init__(
            attribute=DeviceAttribute.CARBON_DIOXIDE_LEVEL,
            device_class=SensorDeviceClass.ENUM,
            options=["Good", "Mediocre", "Harmful", "Risk"],
            **kwargs,
        )


# TODO: is this a valid attribute?
class HubitatCarbonMonoxideLevel(HubitatSensor):
    """A CarbonMonoxideLevel sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a CarbonMonoxideLevel sensor."""
        super().__init__(
            attribute=DeviceAttribute.CARBON_MONOXIDE_LEVEL,
            unit=CONCENTRATION_PARTS_PER_MILLION,
            device_class=SensorDeviceClass.CO,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatVOC(HubitatSensor):
    """A VOC sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a VOC sensor."""
        super().__init__(
            attribute=DeviceAttribute.VOC,
            unit=CONCENTRATION_PARTS_PER_BILLION,
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatVOCLevel(HubitatSensor):
    """A VOC-Level sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a VOC-Level sensor."""
        super().__init__(
            attribute=DeviceAttribute.VOC_LEVEL,
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatHomeHealth(HubitatSensor):
    """A HomeHealth sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a HomeHealth sensor."""
        super().__init__(
            attribute=DeviceAttribute.HOME_HEALTH,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatCurrentSensor(HubitatSensor):
    """A current sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a current sensor."""
        super().__init__(
            attribute=DeviceAttribute.AMPERAGE,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatUVIndexSensor(HubitatSensor):
    """A UV index sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a UV index sensor."""
        super().__init__(
            attribute=DeviceAttribute.UV,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatAqiSensor(HubitatSensor):
    """An AQI sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize an AQI sensor."""
        super().__init__(
            attribute=DeviceAttribute.AQI,
            device_class=SensorDeviceClass.AQI,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatAirQualityIndexSensor(HubitatSensor):
    """An airQualityIndex sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize an airQualityIndex sensor."""
        super().__init__(
            attribute=DeviceAttribute.AIR_QUALITY_INDEX,
            device_class=SensorDeviceClass.AQI,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatPm1Sensor(HubitatSensor):
    """A PM1 sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a PM1 sensor."""
        super().__init__(
            attribute=DeviceAttribute.PM1,
            unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
            device_class=SensorDeviceClass.PM1,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatPm10Sensor(HubitatSensor):
    """A PM10 sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a PM10 sensor."""
        super().__init__(
            attribute=DeviceAttribute.PM10,
            unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
            device_class=SensorDeviceClass.PM10,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatPm25Sensor(HubitatSensor):
    """A PM2.5 sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a PM2.5 sensor."""
        super().__init__(
            attribute=DeviceAttribute.PM25,
            unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatRainRateSensor(HubitatSensor):
    """A rain rate sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a rain rate sensor."""
        super().__init__(
            attribute=DeviceAttribute.RAIN_RATE,
            unit=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
            device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatRainDailySensor(HubitatSensor):
    """A rain daily sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a rain daily sensor."""
        super().__init__(
            attribute=DeviceAttribute.RAIN_DAILY,
            unit=(UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR),
            device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatWindDirectionSensor(HubitatSensor):
    """A wind direction sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a wind direction sensor."""
        super().__init__(
            attribute=DeviceAttribute.WIND_DIRECTION,
            unit=DEGREE,
            device_class=SensorDeviceClass.WIND_SPEED,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatWindSpeedSensor(HubitatSensor):
    """A wind speed sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a wind speed sensor."""
        super().__init__(
            attribute=DeviceAttribute.WIND_SPEED,
            unit=UnitOfSpeed.KILOMETERS_PER_HOUR,
            device_class=SensorDeviceClass.WIND_SPEED,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatWindGustSensor(HubitatSensor):
    """A wind gust sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a wind gust sensor."""
        super().__init__(
            attribute=DeviceAttribute.WIND_GUST,
            unit=UnitOfSpeed.KILOMETERS_PER_HOUR,
            device_class=SensorDeviceClass.WIND_SPEED,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatRateSensor(HubitatSensor):
    """A rate sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a rate sensor."""
        super().__init__(
            attribute=DeviceAttribute.RATE,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatWaterDayPriceSensor(HubitatSensor):
    """A water day liter price sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a water day liter price sensor."""
        super().__init__(
            attribute=DeviceAttribute.DAY_EURO,
            unit=CURRENCY_EURO,
            device_class=SensorDeviceClass.MONETARY,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatWaterDayLiterSensor(HubitatSensor):
    """A water day liter sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a water day liter sensor."""
        super().__init__(
            attribute=DeviceAttribute.DAY_LITER,
            unit=UnitOfVolume.LITERS,
            device_class=SensorDeviceClass.WATER,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatWaterCumulativeLiterSensor(HubitatSensor):
    """A water cumulative liter sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a water cumulative liter sensor."""
        super().__init__(
            attribute=DeviceAttribute.CUMULATIVE_LITER,
            unit=UnitOfVolume.LITERS,
            device_class=SensorDeviceClass.WATER,
            state_class=SensorStateClass.TOTAL_INCREASING,
            **kwargs,
        )


class HubitatWaterCumulativeM3Sensor(HubitatSensor):
    """A water cumulative m3 sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a water cumulative m3 sensor."""
        super().__init__(
            attribute=DeviceAttribute.CUMULATIVE_CUBIC_METER,
            unit=UnitOfVolume.CUBIC_METERS,
            device_class=SensorDeviceClass.WATER,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatWaterDayM3Sensor(HubitatSensor):
    """A water day m3 sensor."""

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize a water day m3 sensor."""
        super().__init__(
            attribute=DeviceAttribute.DAY_CUBIC_METER,
            unit=UnitOfVolume.CUBIC_METERS,
            device_class=SensorDeviceClass.WATER,
            state_class=SensorStateClass.MEASUREMENT,
            **kwargs,
        )


class HubitatUpdateSensor(HubitatSensor):
    """
    A sensor that reports the last time a state update was received for a
    device.
    """

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize an hubitat last update status sensor."""
        super().__init__(
            attribute=DeviceAttribute.LAST_UPDATE,
            device_class=SensorDeviceClass.TIMESTAMP,
            attribute_name="Last Update Time",
            enabled_default=False,
            **kwargs,
        )


class HubitatHsmSensor(HubitatSensor):
    """
    A sensor that reports a hub's HSM status.
    """

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize an hsm status sensor."""
        super().__init__(
            attribute=DeviceAttribute.HSM_STATUS,
            device_class=SensorDeviceClass.ENUM,
            attribute_name="HSM status",
            **kwargs,
        )


class HubitatHubModeSensor(HubitatSensor):
    """
    A sensor that reports a hub's mode.
    """

    def __init__(self, **kwargs: Unpack[HubitatEntityArgs]):
        """Initialize an hsm status sensor."""
        super().__init__(
            attribute=DeviceAttribute.MODE,
            device_class=SensorDeviceClass.ENUM,
            **kwargs,
        )


_SENSOR_ATTRS: tuple[
    tuple[DeviceAttribute, type[HubitatSensor], DeviceCapability | None], ...
] = (
    (DeviceAttribute.AIR_QUALITY_INDEX, HubitatAirQualityIndexSensor, None),
    (DeviceAttribute.AMPERAGE, HubitatCurrentSensor, None),
    (DeviceAttribute.AQI, HubitatAqiSensor, None),
    (DeviceAttribute.BATTERY, HubitatBatterySensor, None),
    (DeviceAttribute.CARBON_DIOXIDE, HubitatCarbonDioxide, None),
    (DeviceAttribute.CARBON_DIOXIDE_LEVEL, HubitatCarbonDioxideLevel, None),
    (DeviceAttribute.CARBON_MONOXIDE_LEVEL, HubitatCarbonMonoxideLevel, None),
    (DeviceAttribute.CUMULATIVE_CUBIC_METER, HubitatWaterCumulativeM3Sensor, None),
    (DeviceAttribute.CUMULATIVE_LITER, HubitatWaterCumulativeLiterSensor, None),
    (DeviceAttribute.DAY_CUBIC_METER, HubitatWaterDayM3Sensor, None),
    (DeviceAttribute.DAY_EURO, HubitatWaterDayPriceSensor, None),
    (DeviceAttribute.DAY_LITER, HubitatWaterDayLiterSensor, None),
    (DeviceAttribute.DEW_POINT, HubitatDewPointSensor, None),
    (DeviceAttribute.ENERGY, HubitatEnergySensor, None),
    (DeviceAttribute.ENERGY_SOURCE, HubitatEnergySourceSensor, None),
    (DeviceAttribute.HOME_HEALTH, HubitatHomeHealth, None),
    (DeviceAttribute.HUMIDITY, HubitatHumiditySensor, None),
    (DeviceAttribute.ILLUMINANCE, HubitatIlluminanceSensor, None),
    (DeviceAttribute.PM1, HubitatPm1Sensor, None),
    (DeviceAttribute.PM10, HubitatPm10Sensor, None),
    (DeviceAttribute.PM25, HubitatPm25Sensor, None),
    (DeviceAttribute.POWER, HubitatPowerSensor, DeviceCapability.POWER_METER),
    (DeviceAttribute.POWER_SOURCE, HubitatPowerSourceSensor, None),
    (DeviceAttribute.PRESSURE, HubitatPressureSensor, None),
    (DeviceAttribute.RAIN_DAILY, HubitatRainDailySensor, None),
    (DeviceAttribute.RAIN_RATE, HubitatRainRateSensor, None),
    (DeviceAttribute.RATE, HubitatRateSensor, None),
    (DeviceAttribute.TEMPERATURE, HubitatTemperatureSensor, None),
    (DeviceAttribute.UV, HubitatUVIndexSensor, None),
    (DeviceAttribute.VOC, HubitatVOC, None),
    (DeviceAttribute.VOC_LEVEL, HubitatVOCLevel, None),
    (DeviceAttribute.VOLTAGE, HubitatVoltageSensor, None),
    (DeviceAttribute.WIND_DIRECTION, HubitatWindDirectionSensor, None),
    (DeviceAttribute.WIND_GUST, HubitatWindGustSensor, None),
    (DeviceAttribute.WIND_SPEED, HubitatWindSpeedSensor, None),
)


def is_update_sensor(_device: Device, _overrides: dict[str, str] | None = None) -> bool:
    """Every device can have an update sensor."""
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize sensor devices."""

    add_hub_entities(hass, entry, async_add_entities)

    # Add an update sensor for every device
    _ = create_and_add_entities(
        hass, entry, async_add_entities, "sensor", HubitatUpdateSensor, is_update_sensor
    )

    for attr in _SENSOR_ATTRS:
        attr_name, Sensor, capability = attr

        def is_sensor(device: Device, _overrides: dict[str, str] | None = None) -> bool:
            if attr_name not in device.attributes:
                return False
            if capability is not None and capability not in device.capabilities:
                return False
            return True

        _ = create_and_add_entities(
            hass, entry, async_add_entities, "sensor", Sensor, is_sensor
        )

    # Create sensor entities for any attributes that don't correspond to known
    # sensor types
    unknown_entities: list[HubitatEntity] = []
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
                        attribute_name=to_display_name(attr),
                        enabled_default=False,
                        device_class=None,
                    )
                )
                _LOGGER.debug(f"Adding generic sensor for {device.id}:{attr}")

    if len(unknown_entities) > 0:
        hub.add_entities(unknown_entities)
        async_add_entities(unknown_entities)
        for entity in unknown_entities:
            entity.load_state()


def add_hub_entities(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add entities for hub services."""

    hub_entities: list[HubitatEntity] = []
    hub = get_hub(hass, entry.entry_id)

    if hub.hsm_supported:
        hub_entities.append(HubitatHsmSensor(hub=hub, device=hub.device))

    if hub.mode_supported:
        hub_entities.append(HubitatHubModeSensor(hub=hub, device=hub.device))

    if len(hub_entities) > 0:
        hub.add_entities(hub_entities)
        async_add_entities(hub_entities)
        for entity in hub_entities:
            entity.load_state()


if TYPE_CHECKING:
    from .hub import DEVICE_TYPECHECK, HUB_TYPECHECK

    test_alarm = HubitatSensor(
        hub=HUB_TYPECHECK,
        device=DEVICE_TYPECHECK,
        attribute=DeviceAttribute.MODE,
    )
