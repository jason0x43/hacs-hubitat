"""Config flow for Hubitat integration."""
from copy import deepcopy
from hubitatmaker import (
    ConnectionError,
    Hub as HubitatHub,
    InvalidConfig,
    InvalidToken,
    RequestError,
)
from hubitatmaker.types import Device
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union, cast
import voluptuous as vol
from voluptuous.schema_builder import Schema

from homeassistant.config_entries import (
    CONN_CLASS_LOCAL_PUSH,
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST, CONF_TEMPERATURE_UNIT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceEntry, DeviceRegistry

from .const import (
    CONF_APP_ID,
    CONF_DEVICE_LIST,
    CONF_DEVICE_TYPE_OVERRIDES,
    CONF_DEVICES,
    CONF_SERVER_PORT,
    CONF_SERVER_URL,
    CONF_SERVER_SSL_CERT,
    CONF_SERVER_SSL_KEY,
    DOMAIN,
    STEP_OVERRIDE_LIGHTS,
    STEP_OVERRIDE_SWITCHES,
    STEP_REMOVE_DEVICES,
    STEP_USER,
    TEMP_C,
    TEMP_F,
)
from .light import is_definitely_light, is_light
from .switch import is_switch
from .util import get_hub_short_id

try:
    from homeassistant.data_entry_flow import FlowResult
except Exception:
    FlowResult = Dict[str, Any]


_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_APP_ID): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Optional(CONF_SERVER_URL): str,
        vol.Optional(CONF_SERVER_PORT): int,
        vol.Optional(CONF_SERVER_SSL_CERT): str,
        vol.Optional(CONF_SERVER_SSL_KEY): str,
        vol.Optional(CONF_TEMPERATURE_UNIT, default=TEMP_F): vol.In([TEMP_F, TEMP_C]),
    }
)


class HubitatConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore
    """Handle a config flow for Hubitat."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_PUSH

    hub: Optional[HubitatHub] = None
    device_schema: Schema

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HubitatOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the user step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _validate_input(user_input)
                entry_data = deepcopy(user_input)
                self.hub = info["hub"]

                placeholders: Dict[str, str] = {}
                for key in user_input:
                    if user_input[key] is not None and key in placeholders:
                        placeholders[key] = user_input[key]

                return self.async_create_entry(
                    title=info["label"],
                    data=entry_data,
                    description_placeholders=placeholders,
                )

            except ConnectionError:
                _LOGGER.exception("Connection error")
                errors["base"] = "cannot_connect"
            except InvalidToken:
                _LOGGER.exception("Invalid access token")
                errors["base"] = "invalid_access_token"
            except InvalidConfig:
                _LOGGER.exception("Invalid config")
                errors["base"] = "invalid_hub_config"
            except RequestError:
                _LOGGER.exception("Request error")
                errors["base"] = "request_error"
            except vol.Invalid:
                _LOGGER.exception("Invalid event URL")
                errors["base"] = "invalid_event_url"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        if len(errors) == 0:
            form_errors = None
        else:
            form_errors = errors
            self.hub = None

        return self.async_show_form(
            step_id=STEP_USER,
            data_schema=CONFIG_SCHEMA,
            errors=form_errors,
        )


class HubitatOptionsFlow(OptionsFlow):
    """Handle an options flow for Hubitat."""

    hub: Optional[HubitatHub] = None
    overrides: Dict[str, str] = {}
    should_remove_devices = False

    def __init__(self, config_entry: ConfigEntry):
        """Initialize an options flow."""
        super().__init__()
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(
        self, user_input: Optional[Dict[str, str]] = None
    ) -> FlowResult:
        """Handle integration options."""
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: Optional[Dict[str, str]] = None
    ) -> FlowResult:
        """Handle integration options."""
        entry = self.config_entry
        errors: Dict[str, str] = {}

        _LOGGER.debug("Setting up entry with user input: %s", user_input)

        if user_input is not None:
            try:
                check_input: Dict[str, Union[str, None]] = {
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_APP_ID: entry.data.get(CONF_APP_ID),
                    CONF_ACCESS_TOKEN: entry.data.get(CONF_ACCESS_TOKEN),
                    CONF_SERVER_PORT: user_input.get(CONF_SERVER_PORT),
                    CONF_SERVER_URL: user_input.get(CONF_SERVER_URL),
                    CONF_SERVER_SSL_CERT: user_input.get(CONF_SERVER_SSL_CERT),
                    CONF_SERVER_SSL_KEY: user_input.get(CONF_SERVER_SSL_KEY),
                }

                info = await _validate_input(check_input)
                self.hub = info["hub"]

                self.options[CONF_HOST] = user_input[CONF_HOST]
                self.options[CONF_SERVER_PORT] = user_input.get(CONF_SERVER_PORT)
                self.options[CONF_SERVER_URL] = user_input.get(CONF_SERVER_URL)
                self.options[CONF_SERVER_SSL_CERT] = user_input.get(CONF_SERVER_SSL_CERT)
                self.options[CONF_SERVER_SSL_KEY] = user_input.get(CONF_SERVER_SSL_KEY)
                self.options[CONF_TEMPERATURE_UNIT] = user_input[CONF_TEMPERATURE_UNIT]

                _LOGGER.debug("Moving to device removal step")
                return await self.async_step_remove_devices()
            except ConnectionError:
                _LOGGER.exception("Connection error")
                errors["base"] = "cannot_connect"
            except InvalidToken:
                _LOGGER.exception("Invalid access token")
                errors["base"] = "invalid_access_token"
            except InvalidConfig:
                _LOGGER.exception("Invalid config")
                errors["base"] = "invalid_hub_config"
            except RequestError:
                _LOGGER.exception("Request error")
                errors["base"] = "request_error"
            except vol.Invalid:
                _LOGGER.exception("Invalid event URL")
                errors["base"] = "invalid_event_url"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        if len(errors) == 0:
            form_errors = None
        else:
            form_errors = errors
            self.hub = None

        default_server_url = entry.options.get(
            CONF_SERVER_URL, entry.data.get(CONF_SERVER_URL)
        )
        if default_server_url == "":
            default_server_url = None

        return self.async_show_form(
            step_id=STEP_USER,
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_HOST,
                        default=entry.options.get(CONF_HOST, entry.data.get(CONF_HOST)),
                    ): str,
                    vol.Optional(
                        CONF_SERVER_URL,
                        description={"suggested_value": default_server_url},
                    ): str,
                    vol.Optional(
                        CONF_SERVER_PORT,
                        description={
                            "suggested_value": entry.options.get(
                                CONF_SERVER_PORT, entry.data.get(CONF_SERVER_PORT)
                            )
                        },
                    ): int,
                    vol.Optional(
                        CONF_SERVER_SSL_CERT,
                        description={
                            "suggested_value": entry.options.get(
                                CONF_SERVER_SSL_CERT, entry.data.get(CONF_SERVER_SSL_CERT)
                            )
                        },
                    ): str,
                    vol.Optional(
                        CONF_SERVER_SSL_KEY,
                        description={
                            "suggested_value": entry.options.get(
                                CONF_SERVER_SSL_KEY, entry.data.get(CONF_SERVER_SSL_KEY)
                            )
                        },
                    ): str,
                    vol.Optional(
                        CONF_TEMPERATURE_UNIT,
                        default=entry.options.get(
                            CONF_TEMPERATURE_UNIT, entry.data.get(CONF_TEMPERATURE_UNIT)
                        )
                        or TEMP_F,
                    ): vol.In([TEMP_F, TEMP_C]),
                }
            ),
            errors=form_errors,
        )

    async def async_step_remove_devices(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the device removal step."""
        errors: Dict[str, str] = {}

        assert self.hass is not None

        devices: List[DeviceEntry] = await self.hass.async_create_task(
            _get_devices(cast(HomeAssistant, self.hass), self.config_entry)
        )
        device_schema = vol.Schema(
            {
                vol.Optional(CONF_DEVICES, default=[]): cv.multi_select(
                    {d.id: d.name for d in devices}
                ),
            }
        )

        if user_input is not None:
            ids = [id for id in user_input[CONF_DEVICES]]
            await self.hass.async_create_task(
                _remove_devices(cast(HomeAssistant, self.hass), ids)
            )
            return await self.async_step_override_lights()

        if len(errors) == 0:
            form_errors = None
        else:
            form_errors = errors

        return self.async_show_form(
            step_id=STEP_REMOVE_DEVICES,
            data_schema=device_schema,
            errors=form_errors,
        )

    async def async_step_override_lights(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Let the user manually specify some devices as lights."""

        async def next_step() -> FlowResult:
            return await self.async_step_override_switches()

        return await self._async_step_override_type(
            user_input, "light", STEP_OVERRIDE_LIGHTS, next_step, is_switch
        )

    async def async_step_override_switches(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Let the user manually specify some devices as switches."""

        async def next_step() -> FlowResult:
            # Copy self.options to ensure config entry is recreated
            self.options = {key: self.options[key] for key in self.options}
            self.options[CONF_DEVICE_TYPE_OVERRIDES] = self.overrides
            _LOGGER.debug(f"Set device type overrides to {self.overrides}")
            _LOGGER.debug("Creating entry")
            return self.async_create_entry(title="", data=self.options)

        def is_possible_light(device: Device) -> bool:
            return is_light(device, None) and not is_definitely_light(device)

        return await self._async_step_override_type(
            user_input, "switch", STEP_OVERRIDE_SWITCHES, next_step, is_possible_light
        )

    async def _async_step_override_type(
        self,
        user_input: Optional[Dict[str, Any]],
        platform: str,
        step_id: str,
        next_step: Callable[[], Awaitable[FlowResult]],
        matcher: Callable[[Device], bool],
    ) -> FlowResult:
        errors: Dict[str, str] = {}

        assert self.hub is not None

        await self.hub.load_devices()
        devices = self.hub.devices

        # Store the list of devices in the config flow so that a config entry
        # update will be triggered if devices are added or removed
        self.options[CONF_DEVICE_LIST] = sorted([id for id in devices])

        existing_overrides = self.options.get(CONF_DEVICE_TYPE_OVERRIDES)
        default_value = []

        possible_overrides = {
            id: devices[id].name for id in devices if matcher(devices[id])
        }

        if existing_overrides:
            default_value = [
                id
                for id in existing_overrides
                if existing_overrides[id] == platform and id in possible_overrides
            ]

        device_schema = vol.Schema(
            {
                vol.Optional(CONF_DEVICES, default=default_value): cv.multi_select(
                    possible_overrides
                )
            }
        )

        if user_input is not None:
            for id in possible_overrides:
                if id in user_input[CONF_DEVICES]:
                    self.overrides[id] = platform
                    _LOGGER.debug(f"Overrode device {id} to {platform}")
                elif id in self.overrides:
                    del self.overrides[id]
                    _LOGGER.debug(f"Cleared override for device {id}")
            return await next_step()

        if len(errors) == 0:
            form_errors = None
        else:
            form_errors = errors

        return self.async_show_form(
            step_id=step_id,
            data_schema=device_schema,
            errors=form_errors,
        )


async def _get_devices(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> List[DeviceEntry]:
    """Return the devices associated with a given config entry."""
    dreg = cast(DeviceRegistry, await device_registry.async_get_registry(hass))
    all_devices: Dict[str, DeviceEntry] = dreg.devices
    devices: List[DeviceEntry] = []

    for id in all_devices:
        dev = all_devices[id]
        for entry_id in dev.config_entries:
            if entry_id == config_entry.entry_id:
                devices.append(dev)
                break

    devices.sort(key=lambda e: e.name or "")
    return devices


async def _remove_devices(hass: HomeAssistant, device_ids: List[str]) -> None:
    """Remove a list of devices."""
    _LOGGER.debug("Removing devices: %s", device_ids)
    dreg = cast(DeviceRegistry, await device_registry.async_get_registry(hass))
    for id in device_ids:
        dreg.async_remove_device(id)


async def _validate_input(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that the user input can create a working connection."""

    # data has the keys from CONFIG_SCHEMA with values provided by the user.
    host: str = user_input[CONF_HOST]
    app_id: str = user_input[CONF_APP_ID]
    token: str = user_input[CONF_ACCESS_TOKEN]
    port: Optional[int] = user_input.get(CONF_SERVER_PORT)
    event_url: Optional[str] = user_input.get(CONF_SERVER_URL)

    if event_url:
        event_url = cv.url(event_url)

    hub = HubitatHub(host, app_id, token, port=port, event_url=event_url)
    await hub.check_config()

    return {"label": f"Hubitat ({get_hub_short_id(hub)})", "hub": hub}
