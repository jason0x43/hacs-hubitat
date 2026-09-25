from typing import cast
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.hubitat.hub import Hub
from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from custom_components.hubitat.hubitatmaker.types import Device, Event
from homeassistant.const import UnitOfTemperature


def _create_hub(
    *,
    connected: bool = False,
    configured_temperature_unit: str | None = "F",
    option_temperature_unit: str | None = None,
    ha_temperature_unit: UnitOfTemperature = UnitOfTemperature.FAHRENHEIT,
) -> tuple[Hub, Mock, Mock]:
    hass = Mock()
    hass.add_job = Mock()
    hass.data = {}
    hass.config.config_dir = "/tmp"
    hass.config.units.temperature_unit = ha_temperature_unit

    entry = Mock()
    entry.data = {
        "host": "192.168.1.10",
        "app_id": "123",
        "access_token": "token",
    }
    if configured_temperature_unit is not None:
        entry.data["temperature_unit"] = configured_temperature_unit
    entry.options = {}
    if option_temperature_unit is not None:
        entry.options["temperature_unit"] = option_temperature_unit
    entry.add_update_listener = Mock(return_value=Mock())

    hubitat_hub = Mock()
    hubitat_hub.devices = {}
    device = Mock()
    hub = Hub(hass, entry, 1, hubitat_hub, device)
    hub._is_connected = connected
    return hub, hass, entry


def test_uses_home_assistant_temperature_unit_when_not_configured():
    """Use HA's temperature unit if the entry has no saved choice."""
    hub, _hass, _entry = _create_hub(
        configured_temperature_unit=None,
        ha_temperature_unit=UnitOfTemperature.CELSIUS,
    )

    assert hub.temperature_unit == UnitOfTemperature.CELSIUS


def test_saved_temperature_unit_overrides_home_assistant_default():
    """Keep honoring the temperature unit saved by the integration."""
    hub, _hass, _entry = _create_hub(
        configured_temperature_unit="F",
        ha_temperature_unit=UnitOfTemperature.CELSIUS,
    )

    assert hub.temperature_unit == UnitOfTemperature.FAHRENHEIT


def test_saved_option_temperature_unit_overrides_entry_data():
    """Prefer a saved options value over the legacy entry-data value."""
    hub, _hass, _entry = _create_hub(
        configured_temperature_unit="F",
        option_temperature_unit="C",
        ha_temperature_unit=UnitOfTemperature.FAHRENHEIT,
    )

    assert hub.temperature_unit == UnitOfTemperature.CELSIUS


@pytest.mark.asyncio
async def test_options_update_to_unset_temperature_unit_reloads_entities():
    """Reload entities when an explicit temperature unit is removed."""
    hub = Mock()
    hub.host = "host"
    hub.port = 0
    hub.event_url = None
    hub._temperature_unit = "F"
    hub.set_ssl_context = AsyncMock()
    entity = Mock()
    hub.entities = [entity]

    hass = Mock()
    hass.async_add_executor_job = AsyncMock(return_value=None)
    entry = Mock()
    entry.entry_id = "entry-id"
    entry.data = {
        "host": "host",
        "app_id": "123",
        "access_token": "token",
        "temperature_unit": "F",
    }
    entry.options = {"temperature_unit": None}

    with patch("custom_components.hubitat.hub.get_hub", return_value=hub):
        await Hub.async_update_options(hass, entry)

    hub.set_temperature_unit.assert_called_once_with(None)
    entity.load_state.assert_called_once()

    runtime_hub, _hass, _entry = _create_hub(
        configured_temperature_unit="F",
        ha_temperature_unit=UnitOfTemperature.CELSIUS,
    )
    runtime_hub.set_temperature_unit(None)

    assert runtime_hub.temperature_unit == UnitOfTemperature.CELSIUS


@pytest.mark.asyncio
async def test_cached_event_unit_is_applied_when_device_state_omits_unit():
    """Use a persisted event unit when the Maker API state has no unit."""
    hub, _hass, _entry = _create_hub(configured_temperature_unit=None)
    device = Device(
        {
            "id": "9",
            "name": "Virtual Temperature Sensor",
            "label": "Virtual Temperature Sensor",
            "type": "Virtual Temperature Sensor",
            "attributes": [
                {
                    "name": DeviceAttribute.TEMPERATURE,
                    "currentValue": 21,
                    "dataType": "NUMBER",
                    "unit": None,
                }
            ],
            "capabilities": [],
            "commands": [],
        }
    )
    cast(dict[str, Device], hub._hub.devices)["9"] = device
    with patch.object(
        hub._attribute_unit_store,
        "async_load",
        AsyncMock(return_value={"9": {"temperature": "°C"}}),
    ):
        await hub.async_load_cached_attribute_units()
    hub.apply_cached_attribute_units()

    assert device.attributes[DeviceAttribute.TEMPERATURE].unit == "°C"


def test_event_unit_overrides_cached_unit_and_is_persisted():
    """An event unit takes precedence and replaces stale cached data."""
    hub, _hass, _entry = _create_hub()
    hub._cached_attribute_units = {"9": {"temperature": "°F"}}
    event = Event(
        {
            "deviceId": "9",
            "name": "temperature",
            "value": "21",
            "unit": "°C",
        }
    )

    with patch.object(hub._attribute_unit_store, "async_delay_save") as delay_save:
        hub._cache_attribute_unit(event)

    assert hub._cached_attribute_units == {"9": {"temperature": "°C"}}
    delay_save.assert_called_once()


def test_cached_unit_does_not_override_a_unit_from_device_state():
    """Use Maker API state units ahead of the persisted fallback."""
    hub, _hass, _entry = _create_hub()
    device = Device(
        {
            "id": "9",
            "name": "Virtual Temperature Sensor",
            "label": "Virtual Temperature Sensor",
            "type": "Virtual Temperature Sensor",
            "attributes": [
                {
                    "name": DeviceAttribute.TEMPERATURE,
                    "currentValue": 21,
                    "dataType": "NUMBER",
                    "unit": "°F",
                }
            ],
            "capabilities": [],
            "commands": [],
        }
    )
    cast(dict[str, Device], hub._hub.devices)["9"] = device
    hub._cached_attribute_units = {"9": {"temperature": "°C"}}

    hub.apply_cached_attribute_units()

    assert device.attributes[DeviceAttribute.TEMPERATURE].unit == "°F"


def test_unitless_event_uses_the_cached_unit():
    """A unit-less event does not erase the last known unit."""
    hub, _hass, _entry = _create_hub()
    device = Device(
        {
            "id": "9",
            "name": "Virtual Temperature Sensor",
            "label": "Virtual Temperature Sensor",
            "type": "Virtual Temperature Sensor",
            "attributes": [
                {
                    "name": DeviceAttribute.TEMPERATURE,
                    "currentValue": 21,
                    "dataType": "NUMBER",
                    "unit": "°C",
                }
            ],
            "capabilities": [],
            "commands": [],
        }
    )
    cast(dict[str, Device], hub._hub.devices)["9"] = device
    hub._cached_attribute_units = {"9": {"temperature": "°C"}}
    hub._device_listeners["9"] = []
    device.update_attr(DeviceAttribute.TEMPERATURE, "22", None)

    hub.handle_event(
        Event(
            {
                "deviceId": "9",
                "name": "temperature",
                "value": "22",
            }
        )
    )

    assert device.attributes[DeviceAttribute.TEMPERATURE].unit == "°C"


def test_set_connected_dispatches_connection_listeners_via_hass_job():
    """Connection listeners should be scheduled on the HA event loop."""
    hub, hass, _entry = _create_hub()
    listener = Mock()
    hub.add_connection_listener(listener)

    hub.set_connected(True)

    assert hub.is_connected is True
    hass.add_job.assert_called_once()
    scheduled_callback, scheduled_listener = hass.add_job.call_args.args
    assert scheduled_listener is listener

    scheduled_callback(scheduled_listener)
    listener.assert_called_once_with(True)


def test_set_connected_does_not_notify_when_state_is_unchanged():
    """No listener work should be scheduled when the connection state is unchanged."""
    hub, hass, _entry = _create_hub(connected=True)
    hub.add_connection_listener(Mock())

    hub.set_connected(True)

    hass.add_job.assert_not_called()
