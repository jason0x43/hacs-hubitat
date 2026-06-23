from unittest.mock import patch

import aiohttp
import pytest
from aiohttp.test_utils import unused_port
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hubitat.const import DOMAIN, H_CONF_HUBITAT_EVENT, PLATFORMS
from custom_components.hubitat.hub import Hub, get_hub
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.helpers import area_registry, device_registry

from tests.conftest import FakeHubitat, get_state_entity_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.allow_hosts(["127.0.0.1", "localhost"]),
]


async def _setup_entry(hass, fake_hubitat: FakeHubitat) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Hubitat (aa:bb:cc:dd:ee:ff)",
        data=fake_hubitat.config_entry_data,
        options=fake_hubitat.config_entry_options,
        unique_id=fake_hubitat.hub_id,
        version=2,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


async def _unload_entry(hass, entry: MockConfigEntry) -> None:
    if entry.state is ConfigEntryState.LOADED:
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


def _assert_connection_state(hub: Hub, expected: bool) -> None:
    assert hub.is_connected is expected


async def test_hub_setup_uses_real_hass_registries_and_maker_api(
    hass, fake_hubitat: FakeHubitat
) -> None:
    entry = await _setup_entry(hass, fake_hubitat)
    try:
        hub = get_hub(hass, entry.entry_id)

        assert hub.is_connected is True
        assert hub.id == fake_hubitat.hub_id
        assert {request["path"] for request in fake_hubitat.requests} >= {
            "/apps/api/123/devices",
            "/apps/api/123/devices/176",
            "/apps/api/123/devices/6",
            "/apps/api/123/modes",
            "/apps/api/123/hsm",
        }
        assert fake_hubitat.post_urls

        switch_entity_id = get_state_entity_id(hass, "switch", "Loft Fan")
        assert hass.states.get(switch_entity_id).state == STATE_OFF

        assert hass.states.get("binary_sensor.hub_status").state == STATE_ON

        dreg = device_registry.async_get(hass)
        assert dreg.async_get_device({(DOMAIN, fake_hubitat.hub_id)}) is not None
        assert (
            dreg.async_get_device({(DOMAIN, f"{fake_hubitat.hub_id}:176")}) is not None
        )

        areg = area_registry.async_get(hass)
        assert areg.async_get_area_by_name("Loft") is not None
        assert areg.async_get_area_by_name("Office") is not None
    finally:
        await _unload_entry(hass, entry)


async def test_hub_event_receiver_updates_entity_state(
    hass, fake_hubitat: FakeHubitat
) -> None:
    entry = await _setup_entry(hass, fake_hubitat)
    try:
        switch_entity_id = get_state_entity_id(hass, "switch", "Loft Fan")
        events = []
        hass.bus.async_listen(H_CONF_HUBITAT_EVENT, lambda event: events.append(event))
        event_url = fake_hubitat.post_urls[-1]

        async with aiohttp.ClientSession() as session:
            response = await session.post(
                f"{event_url}/",
                json={
                    "content": {
                        "name": "switch",
                        "value": "on",
                        "displayName": "Loft Fan",
                        "descriptionText": "Loft Fan is on",
                        "deviceId": "176",
                        "unit": None,
                        "data": None,
                    }
                },
            )

        assert response.status == 200
        await hass.async_block_till_done()
        assert hass.states.get(switch_entity_id).state == STATE_ON
        assert events == []
    finally:
        await _unload_entry(hass, entry)


async def test_hub_services_send_commands_through_maker_api(
    hass, fake_hubitat: FakeHubitat
) -> None:
    entry = await _setup_entry(hass, fake_hubitat)
    try:
        switch_entity_id = get_state_entity_id(hass, "switch", "Loft Fan")

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {"entity_id": switch_entity_id},
            blocking=True,
        )
        await hass.async_block_till_done()

        assert fake_hubitat.commands == [
            {"device_id": "176", "command": "on", "argument": None}
        ]
    finally:
        await _unload_entry(hass, entry)


async def test_offline_hub_can_connect_later_without_duplicate_platform_setup(
    hass, fake_hubitat: FakeHubitat
) -> None:
    fake_hubitat.online = False
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Hubitat",
        data=fake_hubitat.config_entry_data,
        options=fake_hubitat.config_entry_options,
        unique_id=fake_hubitat.hub_id,
        version=2,
    )
    entry.add_to_hass(hass)

    try:
        with patch("custom_components.hubitat.STARTUP_CONNECT_TIMEOUT", 1):
            await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED

        hub = get_hub(hass, entry.entry_id)
        _assert_connection_state(hub, False)
        assert get_state_entity_id(hass, "binary_sensor", "Hub Status")

        fake_hubitat.online = True
        await hub.async_connect()
        hub.cancel_retry_task()
        await hass.async_block_till_done()

        _assert_connection_state(hub, True)
        assert set(hub.get_unsetup_platforms()) == set()
        assert get_state_entity_id(hass, "switch", "Loft Fan")
    finally:
        await _unload_entry(hass, entry)


async def test_hub_unload_stops_event_server_and_cleans_domain_data(
    hass, fake_hubitat: FakeHubitat
) -> None:
    event_server_port = unused_port()
    fake_hubitat.event_server_port = event_server_port
    entry = await _setup_entry(hass, fake_hubitat)
    hub = get_hub(hass, entry.entry_id)
    event_url = hub.event_url

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data[DOMAIN]

    # Reloading after unload proves the old listener released its port and
    # entity/event listeners were cleaned up enough for a fresh setup.
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    reloaded_hub = get_hub(hass, entry.entry_id)
    assert reloaded_hub.port == event_server_port
    assert reloaded_hub.event_url == event_url
    assert set(reloaded_hub.get_unsetup_platforms(PLATFORMS)) == set()
