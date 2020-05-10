from typing import Callable, Iterable

from homeassistant.helpers.entity import Entity

EntityAdder = Callable[[Iterable[Entity]], None]
