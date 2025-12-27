from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from json import loads
from types import MappingProxyType
from typing import Any, Literal, NotRequired, TypedDict, cast, override

from custom_components.hubitat.hubitatmaker.const import DeviceAttribute


class AttributeData(TypedDict):
    name: DeviceAttribute
    dataType: Literal[
        "ENUM",
        "STRING",
        "DYNAMIC_ENUM",
        "JSON_OBJECT",
        "NUMBER",
        "DATE",
        "VECTOR3",
    ]
    currentValue: str | float | datetime
    unit: str | None
    values: NotRequired[list[str]]


class Attribute:
    _properties: AttributeData

    def __init__(self, properties: AttributeData):
        self._properties = properties

    @property
    def name(self) -> str:
        return self._properties["name"]

    @property
    def type(self) -> str:
        return self._properties["dataType"]

    @property
    def value(self) -> str | float | datetime | None:
        return self._properties["currentValue"]

    @property
    def float_value(self) -> float | None:
        val = self.value
        if val is None:
            return None
        if isinstance(val, datetime):
            return float(val.timestamp())
        return float(val)

    @property
    def int_value(self) -> int | None:
        val = self.float_value
        if val is None:
            return None
        return round(val)

    @property
    def str_value(self) -> str | None:
        val = self.value
        if val is None:
            return None
        return str(val)

    @property
    def list_value(self) -> list[Any] | None:
        val = self.str_value
        if val is None:
            return None
        return cast(list[Any], loads(val))

    @property
    def dict_value(self) -> dict[str, Any] | None:
        val = self.str_value
        if val is None:
            return None
        return cast(dict[str, Any], loads(val))

    @property
    def values(self) -> list[str] | None:
        if "values" not in self._properties:
            return None
        return self._properties["values"]

    def update_value(
        self, value: str | float | datetime, unit: str | None = None
    ) -> None:
        self._properties["currentValue"] = value
        self._properties["unit"] = unit

    @property
    def unit(self) -> str | None:
        return self._properties.get("unit")

    def __iter__(self):
        for key in "name", "type", "value", "unit":
            yield key, getattr(self, key)

    @override
    def __str__(self):
        return (
            f'<Attribute name="{self.name}" type="{self.type}" value="{self.value}"'
            f' unit="{self.unit}">'
        )


class Device:
    _properties: dict[str, Any]
    _attributes_ro: MappingProxyType[DeviceAttribute, Attribute]

    def __init__(self, properties: dict[str, Any]):
        self.update_state(properties)

    @property
    def id(self) -> str:
        return cast(str, self._properties["id"])

    @property
    def name(self) -> str:
        return cast(str, self._properties["name"])

    @property
    def label(self) -> str:
        return cast(str, self._properties["label"])

    @property
    def type(self) -> str:
        return cast(str, self._properties["type"])

    @property
    def model(self) -> str | None:
        return self._properties.get("model")

    @property
    def manufacturer(self) -> str | None:
        return self._properties.get("manufacturer")

    @property
    def room(self) -> str | None:
        return self._properties.get("room")

    @property
    def attributes(self) -> Mapping[DeviceAttribute, Attribute]:
        return self._attributes_ro

    @property
    def capabilities(self) -> Sequence[str]:
        return self._capabilities

    @property
    def commands(self) -> Sequence[str]:
        return self._commands

    def update_attr(
        self,
        attr_name: DeviceAttribute,
        value: str | int,
        value_unit: str | None,
    ) -> None:
        attr = self.attributes[attr_name]
        attr.update_value(value, value_unit)

        # Update a virtual hubitat_last_update attribute
        self.attributes[DeviceAttribute.LAST_UPDATE].update_value(datetime.now(UTC))

    def update_state(self, properties: dict[str, Any]) -> None:
        self._properties = properties

        self._attributes: dict[DeviceAttribute, Attribute] = {}
        self._attributes_ro = MappingProxyType(self._attributes)
        attrs = cast(list[AttributeData], properties.get("attributes", []))
        for attr in attrs:
            self._attributes[attr["name"]] = Attribute(attr)

        cap_list = cast(list[str | int], properties.get("capabilities", []))
        caps: list[str] = [p for p in cap_list if isinstance(p, str)]
        self._capabilities: tuple[str, ...] = tuple(caps)

        cmd_list = cast(list[str | int], properties.get("commands", []))
        commands: list[str] = [p for p in cmd_list if isinstance(p, str)]
        self._commands: tuple[str, ...] = tuple(commands)

        self._attributes[DeviceAttribute.LAST_UPDATE] = Attribute(
            {
                "name": DeviceAttribute.HUBITAT_LAST_UPDATE,
                "dataType": "NUMBER",
                "currentValue": datetime.now(UTC),
                "unit": None,
            }
        )

    def __iter__(self):
        for key in (
            "id",
            "name",
            "label",
            "type",
            "model",
            "manufacturer",
            "room",
            "attributes",
            "capabilities",
        ):
            yield key, getattr(self, key)

    @override
    def __str__(self) -> str:
        return (
            f'<Device id="{self.id}" name="{self.name}" label="{self.label}"'
            f' type="{self.type}" model="{self.model}"'
            f' manufacturer="{self.manufacturer}" room="{self.room}">'
        )


class Event:
    _properties: dict[str, Any]

    def __init__(self, properties: dict[str, Any]):
        self._properties = properties

    @property
    def device_id(self) -> str:
        return cast(str, self._properties["deviceId"])

    @property
    def device_name(self) -> str | None:
        return self._properties.get("displayName")

    @property
    def description(self) -> str | None:
        return self._properties.get("descriptionText")

    @property
    def attribute(self) -> str:
        return cast(str, self._properties["name"])

    @property
    def type(self) -> str | None:
        return self._properties.get("type")

    @property
    def value(self) -> str | float:
        return cast(str | float, self._properties["value"])

    @property
    def unit(self) -> str | None:
        return self._properties.get("unit")

    def __iter__(self):
        for key in (
            "device_id",
            "device_name",
            "attribute",
            "value",
            "unit",
            "description",
            "type",
        ):
            yield key, getattr(self, key)

    @override
    def __str__(self) -> str:
        return (
            f'<Event device_id="{self.device_id}" device_name="{self.device_name}"'
            f' attribute="{self.attribute}" value="{self.value}" unit="{self.unit}"'
            f' description="{self.description}" type="{self.type}">'
        )


class Mode:
    _properties: dict[str, Any]

    def __init__(self, properties: dict[str, Any]):
        self._properties = properties

    @property
    def active(self) -> bool:
        return cast(bool, self._properties["active"])

    @active.setter
    def active(self, value: bool) -> None:
        self._properties["active"] = value

    @property
    def id(self) -> int:
        return cast(int, self._properties.get("id", -1))

    @property
    def name(self) -> str:
        return cast(str, self._properties["name"])

    def __iter__(self):
        for key in (
            "active",
            "id",
            "name",
        ):
            yield key, getattr(self, key)

    @override
    def __str__(self) -> str:
        return f'<Mode id="{self.id}" name="{self.name}" active="{self.active}">'
