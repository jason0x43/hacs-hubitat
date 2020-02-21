"""Config flow for Hubitat integration."""
from copy import deepcopy
import logging
from typing import Any, Dict, Optional, Union

from hubitatmaker import (
    ConnectionError,
    InvalidConfig,
    InvalidInfo,
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
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST, CONF_PORT, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant, callback

from .const import CONF_APP_ID, CONF_SERVER_PORT, DOMAIN
from .device import Hub

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_APP_ID): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Optional(CONF_SERVER_PORT): str,
    }
)


async def validate_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""

    # data has the keys from OPTIONS_SCHEMA with values provided by the user.
    hub = Hub(data[CONF_HOST], data[CONF_APP_ID], data[CONF_ACCESS_TOKEN])

    await hub.check_config()

    return {
        "label": f"Hubitat ({hub.mac})",
    }


class HubitatConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hubitat."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_PUSH

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        return HubitatOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: Dict[str, Any] = None
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
            except InvalidInfo:
                _LOGGER.exception("Invalid info")
                errors["base"] = "invalid_hub_info"
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

    async def async_step_init(self, user_input=None) -> Dict[str, Any]:
        """Handle integration options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None) -> Dict[str, Any]:
        """Handle integration options."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self.options[CONF_SERVER_PORT] = user_input[CONF_SERVER_PORT]
            return self.async_create_entry(title="", data=self.options)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SERVER_PORT,
                        default=self.config_entry.options.get(CONF_SERVER_PORT),
                    ): str
                }
            ),
        )
