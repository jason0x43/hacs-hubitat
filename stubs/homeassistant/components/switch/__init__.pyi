from homeassistant.helpers.entity import ToggleEntity

DEVICE_CLASS_OUTLET: str
DEVICE_CLASS_SWITCH: str

class SwitchEntity(ToggleEntity): ...
