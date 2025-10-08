from typing import Callable

from custom_components.hubitat.hub import Hub
from homeassistant.core import HomeAssistant

GetHub = Callable[[HomeAssistant, str], Hub]
