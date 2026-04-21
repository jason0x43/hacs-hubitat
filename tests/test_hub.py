from unittest.mock import Mock

from custom_components.hubitat.hub import Hub


def _create_hub(*, connected: bool = False) -> tuple[Hub, Mock, Mock]:
    hass = Mock()
    hass.add_job = Mock()

    entry = Mock()
    entry.data = {
        "host": "192.168.1.10",
        "app_id": "123",
        "access_token": "token",
        "temperature_unit": "F",
    }
    entry.options = {}
    entry.add_update_listener = Mock(return_value=Mock())

    hubitat_hub = Mock()
    device = Mock()
    hub = Hub(hass, entry, 1, hubitat_hub, device)
    hub._is_connected = connected
    return hub, hass, entry


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
