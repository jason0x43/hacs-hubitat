import json
from datetime import datetime
from os.path import dirname, join

from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from custom_components.hubitat.hubitatmaker.types import Device

with open(join(dirname(__file__), "device_details.json")) as f:
    device_details = json.loads(f.read())


def test_device_can_serialize() -> None:
    """A device should be serializable."""
    d = Device(device_details["6"])
    assert (
        f"{d}"
        == '<Device id="6" name="Generic Z-Wave Contact Sensor" label="Office Door"'
        ' type="Generic Z-Wave Contact Sensor" model="None"'
        ' manufacturer="None" room="Office">'
    )


def test_device_records_last_update_time() -> None:
    """A device should be serializable."""
    d = Device(device_details["6"])
    update_attr = d.attributes[DeviceAttribute.LAST_UPDATE]
    assert update_attr is not None

    last_update = update_attr.value
    assert isinstance(last_update, datetime)
    # HomeAssistant requires datetimes to have timezone info
    assert last_update.tzinfo is not None

    d.update_attr(DeviceAttribute.CONTACT, "closed", None)
    assert last_update != update_attr.value
