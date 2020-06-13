"""Config flow for Hubitat integration."""
from copy import deepcopy
import logging
from typing import Any, Dict, Optional

from hubitatmaker import (
    ConnectionError,
    Hub as HubitatHub,
    InvalidConfig,
    InvalidToken,
    RequestError,
)
import voluptuous as vol

from homeassistant.config_entries import (
    CONN_CLASS_LOCAL_PUSH,
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST, CONF_TEMPERATURE_UNIT
from homeassistant.core import callback

from .const import CONF_APP_ID, CONF_SERVER_PORT, DOMAIN, TEMP_C, TEMP_F
from .util import get_hub_short_id

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_APP_ID): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Optional(CONF_SERVER_PORT, default=0): int,
        vol.Optional(CONF_TEMPERATURE_UNIT, default=TEMP_F): vol.In([TEMP_F, TEMP_C]),
    }
)


async def validate_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that the user input allows us to connect."""

    # data has the keys from CONFIG_SCHEMA with values provided by the user.
    host: str = data[CONF_HOST]
    app_id: str = data[CONF_APP_ID]
    token: str = data[CONF_ACCESS_TOKEN]

    hub = HubitatHub(host, app_id, token)
    await hub.check_config()

    return {"label": f"Hubitat ({get_hub_short_id(hub)})"}


class HubitatConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore
    """Handle a config flow for Hubitat."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_PUSH

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HubitatOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle the user step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(user_input)
                entry_data = deepcopy(user_input)

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
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        if len(errors) == 0:
            form_errors = None
        else:
            form_errors = errors

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=form_errors,
        )


class HubitatOptionsFlow(OptionsFlow):
    """Handle an options flow for Hubitat."""

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

        if user_input is not None:
            try:
                check_input = {
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_APP_ID: entry.data.get(CONF_APP_ID),
                    CONF_ACCESS_TOKEN: entry.data.get(CONF_ACCESS_TOKEN),
                }
                await validate_input(check_input)

                self.options[CONF_HOST] = user_input[CONF_HOST]
                self.options[CONF_SERVER_PORT] = user_input[CONF_SERVER_PORT]
                self.options[CONF_TEMPERATURE_UNIT] = user_input[CONF_TEMPERATURE_UNIT]
                return self.async_create_entry(title="", data=self.options)
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
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        if len(errors) == 0:
            form_errors = None
        else:
            form_errors = errors

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_HOST,
                        default=entry.options.get(CONF_HOST, entry.data.get(CONF_HOST)),
                    ): str,
                    vol.Optional(
                        CONF_SERVER_PORT,
                        default=entry.options.get(
                            CONF_SERVER_PORT, entry.data.get(CONF_SERVER_PORT)
                        )
                        or 0,
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
