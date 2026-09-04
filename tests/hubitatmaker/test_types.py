import json
from datetime import datetime
from os.path import dirname, join
from typing import Any, cast

from custom_components.hubitat.hubitatmaker.const import DeviceAttribute
from custom_components.hubitat.hubitatmaker.types import Attribute, Device

with open(join(dirname(__file__), "device_details.json")) as f:
    device_details = cast(dict[str, Any], json.loads(f.read()))


def test_device_can_serialize() -> None:
    """A device should be serializable."""
    d = Device(cast(dict[str, Any], device_details["6"]))
    assert (
        f"{d}"
        == '<Device id="6" name="Generic Z-Wave Contact Sensor" label="Office Door"'
        + ' type="Generic Z-Wave Contact Sensor" model="None"'
        + ' manufacturer="None" room="Office">'
    )


def test_device_records_last_update_time() -> None:
    """A device should be serializable."""
    d = Device(cast(dict[str, Any], device_details["6"]))
    update_attr = d.attributes[DeviceAttribute.LAST_UPDATE]
    assert update_attr is not None

    last_update = update_attr.value
    assert isinstance(last_update, datetime)
    # HomeAssistant requires datetimes to have timezone info
    assert last_update.tzinfo is not None

    d.update_attr(DeviceAttribute.CONTACT, "closed", None)
    assert last_update != update_attr.value


def test_attribute_sanitizes_html_wrapped_enum_value() -> None:
    """Test enum values wrapped in HTML are normalized to the declared value."""
    attr = Attribute(
        {
            "name": DeviceAttribute.CONTACT,
            "dataType": "ENUM",
            "currentValue": '<span style="color:green">closed</span>',
            "unit": None,
            "values": ["open", "closed"],
        }
    )

    assert attr.value == "closed"

    attr.update_value('<span style="color:red">open</span>', None)
    assert attr.value == "open"


def test_attribute_does_not_sanitize_unrecognized_enum_value() -> None:
    """Test HTML is retained when stripping it would not yield a valid enum value."""
    attr = Attribute(
        {
            "name": DeviceAttribute.CONTACT,
            "dataType": "ENUM",
            "currentValue": "<span> open</span>",
            "unit": None,
            "values": ["open", "closed"],
        }
    )

    assert attr.value == "<span> open</span>"

    attr.update_value("<span>also unknown</span>", None)
    assert attr.value == "<span>also unknown</span>"


def test_attribute_sanitizes_html_wrapped_dynamic_enum_value() -> None:
    """Test dynamic enum values follow the same sanitization rules."""
    attr = Attribute(
        {
            "name": DeviceAttribute.CONTACT,
            "dataType": "DYNAMIC_ENUM",
            "currentValue": "<span>open</span>",
            "unit": None,
            "values": ["open", "closed"],
        }
    )

    assert attr.value == "open"
