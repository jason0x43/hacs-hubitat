"""Config flow for Hubitat integration."""

import logging
from collections.abc import Awaitable
from copy import deepcopy
from typing import Any, Callable, TypedDict, override

import voluptuous as vol
from voluptuous.schema_builder import Schema

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import (
    CONN_CLASS_LOCAL_PUSH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithConfigEntry,
)
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST, CONF_TEMPERATURE_UNIT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceEntry

from .const import (
    DOMAIN,
    H_CONF_APP_ID,
    H_CONF_DEVICE_LIST,
    H_CONF_DEVICE_TYPE_OVERRIDES,
    H_CONF_DEVICES,
    H_CONF_SERVER_PORT,
    H_CONF_SERVER_SSL_CERT,
    H_CONF_SERVER_SSL_KEY,
    H_CONF_SERVER_URL,
    H_CONF_SYNC_AREAS,
    TEMP_C,
    TEMP_F,
    ConfigStep,
    Platform,
)
from .hubitatmaker import (
    ConnectionError,
    Hub as HubitatHub,
    InvalidConfig,
    InvalidToken,
    RequestError,
)
from .hubitatmaker.types import Device
from .light import is_definitely_light, is_light
from .switch import is_switch
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
        vol.Optional(CONF_TEMPERATURE_UNIT, default=TEMP_F): vol.In([TEMP_F, TEMP_C]),
        vol.Optional(H_CONF_SYNC_AREAS, default=False): bool,
    }
)


class HubitatConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore
    """Handle a config flow for Hubitat."""

    VERSION: int = 1
    CONNECTION_CLASS: str = CONN_CLASS_LOCAL_PUSH

    hub: HubitatHub | None = None
    device_schema: Schema | None = None

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HubitatOptionsFlow(config_entry)

    # TODO: remove the 'type: ignore' when were not falling back on
    # FlowResult
    @override
    async def async_step_user(  # type: ignore
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _validate_input(user_input)
                entry_data = deepcopy(user_input)
                self.hub = info["hub"]

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

    hub: HubitatHub | None = None
    overrides: dict[str, str] = {}
    should_remove_devices: bool = False

    def __init__(self, config_entry: ConfigEntry):
        """Initialize an options flow."""
        super().__init__(config_entry)

    async def async_step_init(
        self, _user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle integration options."""
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle integration options."""
        entry = self.config_entry
        errors: dict[str, str] = {}

        _LOGGER.debug("Setting up entry with user input: %s", user_input)

        if user_input is not None:
            try:
                check_input: dict[str, str | None] = {
                    CONF_HOST: user_input[CONF_HOST],
                    H_CONF_APP_ID: entry.data.get(H_CONF_APP_ID),
                    CONF_ACCESS_TOKEN: entry.data.get(CONF_ACCESS_TOKEN),
                    H_CONF_SERVER_PORT: user_input.get(H_CONF_SERVER_PORT),
                    H_CONF_SERVER_URL: user_input.get(H_CONF_SERVER_URL),
                    H_CONF_SERVER_SSL_CERT: user_input.get(H_CONF_SERVER_SSL_CERT),
                    H_CONF_SERVER_SSL_KEY: user_input.get(H_CONF_SERVER_SSL_KEY),
                    H_CONF_SYNC_AREAS: user_input.get(H_CONF_SYNC_AREAS),
                }

                info = await _validate_input(check_input)
                self.hub = info["hub"]

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
                self.options[H_CONF_SYNC_AREAS] = user_input.get(H_CONF_SYNC_AREAS)

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
            step_id=ConfigStep.USER,
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_HOST,
                        default=entry.options.get(CONF_HOST, entry.data.get(CONF_HOST)),
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
                    ): vol.In([TEMP_F, TEMP_C]),
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

    async def async_step_remove_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the device removal step."""
        errors: dict[str, str] = {}

        assert self.hass is not None

        devices = _get_devices(self.hass, self.config_entry)
        device_map = {d.id: d.name for d in devices}

        # Tag the names of devices that appear to have legacy device
        # identifiers (domain + hub_id) so they can be manually removed.
        for d in devices:
            if d.name != "Hubitat Elevation":
                for id in d.identifiers:
                    if len(id) != 2 or ":" not in id[1]:
                        device_map[d.id] = f"{d.name}*"
                        break

        device_schema = vol.Schema(
            {
                vol.Optional(H_CONF_DEVICES, default=[]): cv.multi_select(device_map),
            }
        )

        if user_input is not None:
            conf_devs: list[str] = user_input[H_CONF_DEVICES]
            ids = [id for id in conf_devs]
            _remove_devices(self.hass, ids)
            return await self.async_step_override_lights()

        if len(errors) == 0:
            form_errors = None
        else:
            form_errors = errors

        return self.async_show_form(
            step_id=ConfigStep.REMOVE_DEVICES,
            data_schema=device_schema,
            errors=form_errors,
        )

    async def async_step_override_lights(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user manually specify some devices as lights."""

        async def next_step() -> ConfigFlowResult:
            return await self.async_step_override_switches()

        return await self._async_step_override_type(
            user_input, "light", ConfigStep.OVERRIDE_LIGHTS, next_step, is_switch
        )

    async def async_step_override_switches(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user manually specify some devices as switches."""

        async def next_step() -> ConfigFlowResult:
            # Copy self.options to ensure config entry is recreated
            self.options[H_CONF_DEVICE_TYPE_OVERRIDES] = self.overrides
            _LOGGER.debug(f"Set device type overrides to {self.overrides}")
            _LOGGER.debug("Creating entry")
            return self.async_create_entry(title="", data=self.options)

        def is_possible_light(device: Device) -> bool:
            return is_light(device, None) and not is_definitely_light(device)

        return await self._async_step_override_type(
            user_input,
            "switch",
            ConfigStep.OVERRIDE_SWITCHES,
            next_step,
            is_possible_light,
        )

    async def _async_step_override_type(
        self,
        user_input: dict[str, Any] | None,
        platform: Platform,
        step_id: str,
        next_step: Callable[[], Awaitable[ConfigFlowResult]],
        matcher: Callable[[Device], bool],
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        assert self.hub is not None

        await self.hub.load_devices()
        devices = self.hub.devices

        # Store the list of devices in the config flow so that a config entry
        # update will be triggered if devices are added or removed
        self.options[H_CONF_DEVICE_LIST] = sorted([id for id in devices])

        existing_overrides: dict[str, str] | None = self.options.get(
            H_CONF_DEVICE_TYPE_OVERRIDES
        )
        default_value = []

        possible_overrides = {
            id: devices[id].label for id in devices if matcher(devices[id])
        }

        if existing_overrides:
            default_value = [
                id
                for id in existing_overrides
                if existing_overrides[id] == platform and id in possible_overrides
            ]

        device_schema = vol.Schema(
            {
                vol.Optional(H_CONF_DEVICES, default=default_value): cv.multi_select(
                    possible_overrides
                )
            }
        )

        if user_input is not None:
            for id in possible_overrides:
                if id in user_input[H_CONF_DEVICES]:
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


def _get_devices(hass: HomeAssistant, config_entry: ConfigEntry) -> list[DeviceEntry]:
    """Return the devices associated with a given config entry."""
    dreg = device_registry.async_get(hass)
    all_devices = dreg.devices
    devices: list[DeviceEntry] = []

    for id in all_devices:
        dev = all_devices[id]
        for entry_id in dev.config_entries:
            if entry_id == config_entry.entry_id:
                devices.append(dev)
                break

    devices.sort(key=lambda e: e.name or "")
    return devices


def _remove_devices(hass: HomeAssistant, device_ids: list[str]) -> None:
    """Remove a list of devices."""
    _LOGGER.debug("Removing devices: %s", device_ids)
    dreg = device_registry.async_get(hass)
    for id in device_ids:
        dreg.async_remove_device(id)


class ValidatedInput(TypedDict):
    label: str
    hub: HubitatHub


async def _validate_input(user_input: dict[str, Any]) -> ValidatedInput:
    """Validate that the user input can create a working connection."""

    # data has the keys from CONFIG_SCHEMA with values provided by the user.
    host: str = user_input[CONF_HOST]
    app_id: str = user_input[H_CONF_APP_ID]
    token: str = user_input[CONF_ACCESS_TOKEN]
    port: int | None = user_input.get(H_CONF_SERVER_PORT)
    event_url: str | None = user_input.get(H_CONF_SERVER_URL)

    if event_url:
        event_url = cv.url(event_url)

    hub = HubitatHub(host, app_id, token, port=port, event_url=event_url)
    await hub.check_config()

    return {"label": f"Hubitat ({get_hub_short_id(hub)})", "hub": hub}
