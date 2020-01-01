"""Config flow for Hubitat integration."""
from copy import deepcopy
import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST, CONF_WEBHOOK_ID

from .const import CONF_APP_ID, DOMAIN
from .hubitat import (
    ConnectionError,
    HubitatHub,
    InvalidConfig,
    InvalidInfo,
    InvalidToken,
    RequestError,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({CONF_HOST: str, CONF_APP_ID: str, CONF_ACCESS_TOKEN: str})


async def validate_input(hass: core.HomeAssistant, data: Dict[str, Any]):
    """Validate the user input allows us to connect."""

    # data has the keys from DATA_SCHEMA with values provided by the user.
    hub = HubitatHub(data[CONF_HOST], data[CONF_APP_ID], data[CONF_ACCESS_TOKEN])

    await hub.check_config()

    return {
        "mac": hub.mac,
        "id": hub.id,
        "label": f"Hubitat [{hub.id}]",
    }


class HubitatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hubitat."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                entry_data = deepcopy(user_input)
                entry_data[CONF_WEBHOOK_ID] = info["id"]
                return self.async_create_entry(title=info["label"], data=entry_data)
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

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
