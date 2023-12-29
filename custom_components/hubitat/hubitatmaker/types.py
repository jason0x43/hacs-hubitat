from time import time
from types import MappingProxyType
from typing import Any, Mapping, Sequence


class Attribute:
    def __init__(self, properties: dict[str, Any]):
        self._properties = properties

    @property
    def name(self) -> str:
        return self._properties["name"]

    @property
    def type(self) -> str:
        return self._properties["dataType"]

    @property
    def value(self) -> str | float:
        return self._properties["currentValue"]

    @property
    def values(self) -> list[str] | None:
        if "values" not in self._properties:
            return None
        return self._properties["values"]

    def update_value(self, value: str | float, unit: str | None = None) -> None:
        self._properties["currentValue"] = value
        self._properties["unit"] = unit

    @property
    def unit(self) -> str | None:
        return self._properties.get("unit")

    def __iter__(self):
        for key in "name", "type", "value", "unit":
            yield key, getattr(self, key)

    def __str__(self):
        return (
            f'<Attribute name="{self.name}" type="{self.type}" value="{self.value}"'
            f' unit="{self.unit}">'
        )


class Device:
    def __init__(self, properties: dict[str, Any]):
        self.update_state(properties)

    @property
    def id(self) -> str:
        return self._properties["id"]

    @property
    def name(self) -> str:
        return self._properties["name"]

    @property
    def label(self) -> str:
        return self._properties["label"]

    @property
    def type(self) -> str:
        return self._properties["type"]

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
    def attributes(self) -> Mapping[str, Attribute]:
        return self._attributes_ro

    @property
    def capabilities(self) -> Sequence[str]:
        return self._capabilities

    @property
    def commands(self) -> Sequence[str]:
        return self._commands

    @property
    def last_update(self) -> float:
        """
        Return the last time this device was updated as a unix timestamp.
        """
        return self._last_update

    def update_attr(
        self, attr_name: str, value: str | int, value_unit: str | None
    ) -> None:
        attr = self.attributes[attr_name]
        attr.update_value(value, value_unit)
        self._last_update = time()

    def update_state(self, properties: dict[str, Any]) -> None:
        self._properties = properties
        self._last_update = time()

        self._attributes: dict[str, Attribute] = {}
        self._attributes_ro = MappingProxyType(self._attributes)
        for attr in properties.get("attributes", []):
            self._attributes[attr["name"]] = Attribute(attr)

        caps: list[str] = [
            p for p in properties.get("capabilities", []) if isinstance(p, str)
        ]
        self._capabilities: tuple[str, ...] = tuple(caps)

        commands: list[str] = [
            p for p in properties.get("commands", []) if isinstance(p, str)
        ]
        self._commands: tuple[str, ...] = tuple(commands)

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

    def __str__(self):
        return (
            f'<Device id="{self.id}" name="{self.name}" label="{self.label}"'
            f' type="{self.type}" model="{self.model}"'
            f' manufacturer="{self.manufacturer}" room="{self.room}">'
        )


class Event:
    def __init__(self, properties: dict[str, Any]):
        self._properties = properties

    @property
    def device_id(self) -> str:
        return self._properties["deviceId"]

    @property
    def device_name(self) -> str | None:
        return self._properties.get("displayName")

    @property
    def description(self) -> str | None:
        return self._properties.get("descriptionText")

    @property
    def attribute(self) -> str:
        return self._properties["name"]

    @property
    def type(self) -> str | None:
        return self._properties.get("type")

    @property
    def value(self) -> str | float:
        return self._properties["value"]

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

    def __str__(self) -> str:
        return (
            f'<Event device_id="{self.device_id}" device_name="{self.device_name}"'
            f' attribute="{self.attribute}" value="{self.value}" unit="{self.unit}"'
            f' description="{self.description}" type="{self.type}">'
        )


class Mode:
    def __init__(self, properties: dict[str, Any]):
        self._properties = properties

    @property
    def active(self) -> bool:
        return self._properties["active"]

    @active.setter
    def active(self, value: bool) -> None:
        self._properties["active"] = value

    @property
    def id(self) -> int:
        return self._properties.get("id", -1)

    @property
    def name(self) -> str:
        return self._properties["name"]

    def __iter__(self):
        for key in (
            "active",
            "id",
            "name",
        ):
            yield key, getattr(self, key)

    def __str__(self) -> str:
        return f'<Mode id="{self.id}" name="{self.name}" active="{self.active}">'
