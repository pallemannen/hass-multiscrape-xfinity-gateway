"""Config flow for the Xfinity Gateway integration.

Validates the host/username/password against the real gateway before
creating the config entry, using the same multiscrape HTTP-session/
form-authentication building blocks the rest of this integration reuses -
so a bad password or unreachable host is caught immediately in the UI
instead of surfacing later as silently-unavailable sensors.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType
from homeassistant.loader import IntegrationNotFound, async_get_integration

from custom_components.multiscrape.coordinator import create_content_request_manager
from custom_components.multiscrape.http_session import create_http_session

from .const import DEFAULT_HOST, DEFAULT_SCAN_INTERVAL, DOMAIN
from .util import build_scraper_conf

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=30)
        ),
    }
)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect to the gateway."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate the gateway rejected the credentials."""


async def _async_validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Attempt a real login/fetch against the gateway with the given input."""
    scraper_conf = build_scraper_conf(data)
    session = create_http_session(DOMAIN, scraper_conf, hass, None)
    try:
        request_manager = create_content_request_manager(DOMAIN, scraper_conf, hass, session)
        try:
            await request_manager.get_content()
        except httpx.HTTPStatusError as ex:
            if ex.response.status_code in (401, 403):
                raise InvalidAuth from ex
            raise CannotConnect from ex
        except (httpx.TimeoutException, httpx.RequestError) as ex:
            raise CannotConnect from ex
    finally:
        await session.async_close()


class XfinityGatewayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Xfinity Gateway."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial (and only) step."""
        # multiscrape only needs to be *installed* (its modules importable on
        # disk) - we call its functions directly and never rely on its own
        # async_setup() having run, so we deliberately don't declare it as a
        # hard `dependencies` entry in manifest.json (that would require HA
        # to successfully set it up, which fails if the user has no
        # `multiscrape:` YAML config, e.g. because they use it solely for
        # this integration). Check installation explicitly instead.
        try:
            await async_get_integration(self.hass, "multiscrape")
        except IntegrationNotFound:
            return self.async_abort(reason="multiscrape_not_installed")

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _async_validate_input(self.hass, user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - genuinely unknown failure, surface generically
                _LOGGER.exception("Unexpected exception during Xfinity Gateway setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Xfinity Gateway", data=user_input)

        schema = self.add_suggested_values_to_schema(STEP_USER_DATA_SCHEMA, user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
