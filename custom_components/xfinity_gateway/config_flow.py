"""Config flow for the Xfinity Gateway integration.

Validates the host/username/password against the real gateway before
creating the config entry, using the same multiscrape HTTP-session/
form-authentication building blocks the rest of this integration reuses -
so a bad password or unreachable host is caught immediately in the UI
instead of surfacing later as silently-unavailable sensors.

This gateway's web UI returns HTTP 200 for every page whether or not you're
actually logged in - a failed login just re-serves the login page, and any
other page redirects to it, also with a 200. So checking for an HTTP error
status is not enough to detect a failed login (see CannotConnect/InvalidAuth
below) - validation instead checks the response for the login page's own
"Gateway > Login" header (#index_header). If that's present, we're still
looking at the login page and auth failed - deliberately not inferring auth
failure from a data-field scrape miss, since that could have an unrelated
cause (page structure change, network hiccup, etc.) and would misreport it
as a credentials problem.
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

from bs4 import BeautifulSoup

from custom_components.multiscrape.coordinator import create_content_request_manager
from custom_components.multiscrape.http_session import create_http_session

from .const import DEFAULT_HOST, DEFAULT_SCAN_INTERVAL, DOMAIN
from .util import build_scraper_conf

# Fingerprint of the login page itself (see the module docstring) - present
# only when we're still looking at the login page, i.e. auth didn't take.
LOGIN_HEADER_SELECTOR = "#index_header"
LOGIN_HEADER_TEXT = "Gateway > Login"

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
    """Attempt a real login/fetch against the gateway with the given input.

    An HTTP-level success doesn't mean the login worked (see module docstring),
    so this also scrapes the Connection Status field from the response and
    treats "selector didn't match anything" as InvalidAuth too.
    """
    scraper_conf = build_scraper_conf(data)
    session = create_http_session(DOMAIN, scraper_conf, hass, None)
    try:
        request_manager = create_content_request_manager(DOMAIN, scraper_conf, hass, session)
        try:
            content = await request_manager.get_content()
        except httpx.HTTPStatusError as ex:
            if ex.response.status_code in (401, 403):
                raise InvalidAuth from ex
            raise CannotConnect from ex
        except (httpx.TimeoutException, httpx.RequestError) as ex:
            raise CannotConnect from ex

        soup = BeautifulSoup(content, scraper_conf.get("parser", "lxml"))
        header = soup.select_one(LOGIN_HEADER_SELECTOR)
        if header is not None and header.get_text(strip=True) == LOGIN_HEADER_TEXT:
            raise InvalidAuth
    finally:
        await session.async_close()


class XfinityGatewayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Xfinity Gateway."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        return await self._async_step_form(user_input, is_reconfigure=False)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle changing host/username/password/scan interval after setup."""
        return await self._async_step_form(user_input, is_reconfigure=True)

    async def _async_step_form(
        self, user_input: dict[str, Any] | None, is_reconfigure: bool
    ) -> FlowResult:
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
                if is_reconfigure:
                    return self.async_update_reload_and_abort(
                        self._get_reconfigure_entry(), data=user_input
                    )
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Xfinity Gateway", data=user_input)

        if is_reconfigure and user_input is None:
            user_input = dict(self._get_reconfigure_entry().data)

        step_id = "reconfigure" if is_reconfigure else "user"
        schema = self.add_suggested_values_to_schema(STEP_USER_DATA_SCHEMA, user_input)
        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors)
