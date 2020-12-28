"""Config flow for Hubitat integration."""
from copy import deepcopy
import logging
from typing import Any, Dict, List, Optional, Union, cast

from hubitatmaker import (
    ConnectionError,
    Hub as HubitatHub,
    InvalidConfig,
    InvalidToken,
    RequestError,
)
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
    CONF_DEVICES,
    CONF_SERVER_PORT,
    CONF_SERVER_URL,
    DOMAIN,
    TEMP_C,
    TEMP_F,
)
from .util import get_hub_short_id

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_APP_ID): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Optional(CONF_SERVER_URL): str,
        vol.Optional(CONF_SERVER_PORT): int,
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
    ) -> Dict[str, Any]:
        """Handle the user step."""
        errors: Dict[str, str] = {}

        if self.hub:
            return await self.async_step_devices()

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
            step_id="user",
            data_schema=CONFIG_SCHEMA,
            errors=form_errors,
        )

    async def async_step_devices(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle the user step."""
        errors: Dict[str, str] = {}

        if self.device_schema is None:
            await self.hub._load_devices()
            devices = self.hub.devices
            self.device_schema = vol.Schema(
                {vol.Optional(devices[id].name, default=False): str for id in devices}
            )

        if user_input is not None:
            _LOGGER.debug("Updating devices with: %s", user_input)

        if len(errors) == 0:
            form_errors = None
        else:
            form_errors = errors

        return self.async_show_form(
            step_id="devices",
            data_schema=CONFIG_SCHEMA,
            errors=form_errors,
        )


class HubitatOptionsFlow(OptionsFlow):
    """Handle an options flow for Hubitat."""

    device_schema: Optional[Schema] = None
    should_remove_devices = False

    def __init__(self, config_entry: ConfigEntry):
        """Initialize an options flow."""
        super().__init__()
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(
        self, user_input: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Handle integration options."""
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
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
                }
                await _validate_input(check_input)

                self.options[CONF_HOST] = user_input[CONF_HOST]
                self.options[CONF_SERVER_PORT] = user_input.get(CONF_SERVER_PORT)
                self.options[CONF_SERVER_URL] = user_input.get(CONF_SERVER_URL)
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

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_HOST,
                        default=entry.options.get(CONF_HOST, entry.data.get(CONF_HOST)),
                    ): str,
                    vol.Optional(
                        CONF_SERVER_URL,
                        description={
                            "suggested_value": entry.options.get(
                                CONF_SERVER_URL, entry.data.get(CONF_SERVER_URL)
                            )
                        },
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
    ) -> Dict[str, Any]:
        """Handle the user step."""
        errors: Dict[str, str] = {}

        if self.device_schema is None:
            devices: List[DeviceEntry] = await self.hass.async_create_task(
                _get_devices(self.hass, self.config_entry)
            )
            device_dict = {d.id: d.name for d in devices}
            self.device_schema = vol.Schema(
                {
                    vol.Optional(CONF_DEVICES, default=[]): cv.multi_select(
                        device_dict
                    ),
                }
            )

        if user_input is not None:
            ids = [id for id in user_input[CONF_DEVICES]]
            await self.hass.async_create_task(_remove_devices(self.hass, ids))
            return self.async_create_entry(title="", data=self.options)

        if len(errors) == 0:
            form_errors = None
        else:
            form_errors = errors

        return self.async_show_form(
            step_id="remove_devices",
            data_schema=self.device_schema,
            errors=form_errors,
        )


async def _get_devices(
    hass: Optional[HomeAssistant], config_entry: ConfigEntry
) -> List[DeviceEntry]:
    if hass is None:
        return []
    dreg = cast(DeviceRegistry, await device_registry.async_get_registry(hass))
    all_devices: Dict[str, DeviceEntry] = dreg.devices
    devices: List[DeviceEntry] = []

    for id in all_devices:
        dev = all_devices[id]
        for entry_id in dev.config_entries:
            if entry_id == config_entry.entry_id:
                devices.append(dev)
                break

    devices.sort(key=lambda e: e.name)
    return devices


async def _remove_devices(hass: Optional[HomeAssistant], device_ids: List[str]) -> None:
    if hass is None:
        return
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
