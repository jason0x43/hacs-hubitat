"""Config flow for Hubitat integration."""

import logging
from copy import deepcopy
from typing import Any, TypedDict, cast, override

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import (
    CONN_CLASS_LOCAL_PUSH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithConfigEntry,
)
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_HOST,
    CONF_TEMPERATURE_UNIT,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    DOMAIN,
    H_CONF_APP_ID,
    H_CONF_HUB_ID,
    H_CONF_LEGACY_LIGHT_NAME_HEURISTIC,
    H_CONF_SERVER_PORT,
    H_CONF_SERVER_SSL_CERT,
    H_CONF_SERVER_SSL_KEY,
    H_CONF_SERVER_URL,
    H_CONF_SYNC_AREAS,
    H_CONF_SYNC_DEVICES,
    TEMP_C,
    TEMP_F,
    ConfigStep,
)
from .hubitatmaker import (
    ConnectionError,
    Hub as HubitatHub,
    InvalidConfig,
    InvalidToken,
    RequestError,
)
from .util import get_hub_short_id

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(H_CONF_APP_ID): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Optional(H_CONF_SERVER_URL): str,
        vol.Optional(H_CONF_SERVER_PORT): int,
        vol.Optional(H_CONF_SERVER_SSL_CERT): str,
        vol.Optional(H_CONF_SERVER_SSL_KEY): str,
        vol.Optional(CONF_TEMPERATURE_UNIT, default=TEMP_F): SelectSelector(
            SelectSelectorConfig(
                options=[TEMP_F, TEMP_C],
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="temperature_unit",
            )
        ),
        vol.Optional(H_CONF_SYNC_DEVICES, default=True): bool,
        vol.Optional(H_CONF_SYNC_AREAS, default=False): bool,
    }
)


class HubitatConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hubitat."""

    VERSION: int = 2
    MINOR_VERSION: int = 2
    CONNECTION_CLASS: str = CONN_CLASS_LOCAL_PUSH

    hub: HubitatHub | None = None

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HubitatOptionsFlow(config_entry)

    # TODO: remove the 'type: ignore' when were not falling back on
    # FlowResult
    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _validate_input(user_input)
                entry_data = deepcopy(user_input)
                entry_data[H_CONF_LEGACY_LIGHT_NAME_HEURISTIC] = False
                self.hub = info["hub"]

                # Generate hub_id from initial token and store it
                hub_id = get_hub_short_id(self.hub)
                entry_data[H_CONF_HUB_ID] = hub_id

                # Set unique_id to prevent duplicate config entries
                await self.async_set_unique_id(hub_id)
                self._abort_if_unique_id_configured()

                placeholders: dict[str, Any] = {}
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
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", e)
                errors["base"] = "unknown"

        if len(errors) == 0:
            form_errors = None
        else:
            form_errors = errors
            self.hub = None

        return self.async_show_form(
            step_id=ConfigStep.USER,
            data_schema=CONFIG_SCHEMA,
            errors=form_errors,
        )


class HubitatOptionsFlow(OptionsFlowWithConfigEntry):
    """Handle an options flow for Hubitat."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize an options flow."""
        super().__init__(config_entry)

    async def async_step_init(
        self, _user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle integration options."""
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle integration options."""
        entry = self.config_entry
        errors: dict[str, str] = {}

        _LOGGER.debug("Setting up entry with user input: %s", user_input)

        if user_input is not None:
            try:
                # Use new app_id/token if provided, otherwise fall back to existing
                app_id = user_input.get(H_CONF_APP_ID) or entry.data.get(H_CONF_APP_ID)
                access_token = user_input.get(CONF_ACCESS_TOKEN) or entry.data.get(
                    CONF_ACCESS_TOKEN
                )

                check_input: dict[str, str | None] = {
                    CONF_HOST: user_input[CONF_HOST],
                    H_CONF_APP_ID: app_id,
                    CONF_ACCESS_TOKEN: access_token,
                    H_CONF_SERVER_PORT: user_input.get(H_CONF_SERVER_PORT),
                    H_CONF_SERVER_URL: user_input.get(H_CONF_SERVER_URL),
                    H_CONF_SERVER_SSL_CERT: user_input.get(H_CONF_SERVER_SSL_CERT),
                    H_CONF_SERVER_SSL_KEY: user_input.get(H_CONF_SERVER_SSL_KEY),
                    H_CONF_SYNC_AREAS: user_input.get(H_CONF_SYNC_AREAS),
                    H_CONF_SYNC_DEVICES: user_input.get(H_CONF_SYNC_DEVICES),
                }

                _ = await _validate_input(check_input)
                self.options[CONF_HOST] = user_input[CONF_HOST]
                self.options[H_CONF_SERVER_PORT] = user_input.get(H_CONF_SERVER_PORT)
                self.options[H_CONF_SERVER_URL] = user_input.get(H_CONF_SERVER_URL)
                self.options[H_CONF_SERVER_SSL_CERT] = user_input.get(
                    H_CONF_SERVER_SSL_CERT
                )
                self.options[H_CONF_SERVER_SSL_KEY] = user_input.get(
                    H_CONF_SERVER_SSL_KEY
                )
                self.options[CONF_TEMPERATURE_UNIT] = user_input[CONF_TEMPERATURE_UNIT]
                self.options[H_CONF_SYNC_DEVICES] = user_input.get(H_CONF_SYNC_DEVICES)
                self.options[H_CONF_SYNC_AREAS] = user_input.get(H_CONF_SYNC_AREAS)

                # Track if connection values changed (to update entry.data later)
                if user_input.get(H_CONF_APP_ID):
                    self.options[H_CONF_APP_ID] = user_input[H_CONF_APP_ID]
                if user_input.get(CONF_ACCESS_TOKEN):
                    self.options[CONF_ACCESS_TOKEN] = user_input[CONF_ACCESS_TOKEN]

                return self._async_create_entry()
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
        return self.async_show_form(
            step_id=ConfigStep.USER,
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_HOST,
                        default=entry.options.get(CONF_HOST, entry.data.get(CONF_HOST)),
                    ): str,
                    vol.Optional(
                        H_CONF_APP_ID,
                        description={
                            "suggested_value": entry.options.get(
                                H_CONF_APP_ID,
                                entry.data.get(H_CONF_APP_ID),
                            )
                            or ""
                        },
                    ): str,
                    vol.Optional(
                        CONF_ACCESS_TOKEN,
                        description={
                            "suggested_value": entry.options.get(
                                CONF_ACCESS_TOKEN,
                                entry.data.get(CONF_ACCESS_TOKEN),
                            )
                            or ""
                        },
                    ): str,
                    vol.Optional(
                        H_CONF_SERVER_URL,
                        description={
                            "suggested_value": entry.options.get(
                                H_CONF_SERVER_URL,
                                entry.data.get(H_CONF_SERVER_URL),
                            )
                            or ""
                        },
                    ): str,
                    vol.Optional(
                        H_CONF_SERVER_PORT,
                        description={
                            "suggested_value": entry.options.get(
                                H_CONF_SERVER_PORT,
                                entry.data.get(H_CONF_SERVER_PORT),
                            )
                            or ""
                        },
                    ): int,
                    vol.Optional(
                        H_CONF_SERVER_SSL_CERT,
                        description={
                            "suggested_value": entry.options.get(
                                H_CONF_SERVER_SSL_CERT,
                                entry.data.get(H_CONF_SERVER_SSL_CERT),
                            )
                            or ""
                        },
                    ): str,
                    vol.Optional(
                        H_CONF_SERVER_SSL_KEY,
                        description={
                            "suggested_value": entry.options.get(
                                H_CONF_SERVER_SSL_KEY,
                                entry.data.get(H_CONF_SERVER_SSL_KEY),
                            )
                            or ""
                        },
                    ): str,
                    vol.Optional(
                        CONF_TEMPERATURE_UNIT,
                        default=entry.options.get(
                            CONF_TEMPERATURE_UNIT,
                            entry.data.get(CONF_TEMPERATURE_UNIT),
                        )
                        or TEMP_F,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[TEMP_F, TEMP_C],
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="temperature_unit",
                        )
                    ),
                    vol.Optional(
                        H_CONF_SYNC_DEVICES,
                        default=entry.options.get(
                            H_CONF_SYNC_DEVICES,
                            entry.data.get(H_CONF_SYNC_DEVICES, False),
                        ),
                    ): bool,
                    vol.Optional(
                        H_CONF_SYNC_AREAS,
                        default=entry.options.get(
                            H_CONF_SYNC_AREAS,
                            entry.data.get(H_CONF_SYNC_AREAS),
                        )
                        or False,
                    ): bool,
                }
            ),
            errors=form_errors,
        )

    def _async_create_entry(self) -> ConfigFlowResult:
        """Update connection data and create the options entry."""
        entry = self.config_entry
        new_data = {**entry.data}

        for key in (H_CONF_APP_ID, CONF_ACCESS_TOKEN):
            if self.options.get(key) and self.options[key] != entry.data.get(key):
                new_data[key] = self.options.pop(key)

        if new_data != entry.data:
            self.hass.config_entries.async_update_entry(entry, data=new_data)

        return self.async_create_entry(title="", data=self.options)


class ValidatedInput(TypedDict):
    label: str
    hub: HubitatHub


async def _validate_input(user_input: dict[str, Any]) -> ValidatedInput:
    """Validate that the user input can create a working connection."""

    # data has the keys from CONFIG_SCHEMA with values provided by the user.
    host = cast(str, user_input[CONF_HOST])
    app_id = cast(str, user_input[H_CONF_APP_ID])
    token = cast(str, user_input[CONF_ACCESS_TOKEN])
    port: int | None = user_input.get(H_CONF_SERVER_PORT)
    event_url: str | None = user_input.get(H_CONF_SERVER_URL)

    if event_url:
        event_url = cv.url(event_url)

    hub = HubitatHub(host, app_id, token, port=port, event_url=event_url)
    await hub.check_config()

    return {"label": f"Hubitat ({get_hub_short_id(hub)})", "hub": hub}
