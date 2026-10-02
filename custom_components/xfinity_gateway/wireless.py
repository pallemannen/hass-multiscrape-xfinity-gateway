"""Wi-Fi radio state, read from wireless_network_configuration.jst's script."""
from __future__ import annotations

import asyncio
import logging
import re

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.template import Template

from custom_components.multiscrape.const import CONF_SELECT
from custom_components.multiscrape.entity import MultiscrapeEntity
from custom_components.multiscrape.selector import Selector

from .api import GatewayClient, GatewayError
from .const import WIFI_RADIOS, WIFI_SAVE_DELAY, WIRELESS_SCRIPT_SELECTOR
from .util import entity_object_id

_LOGGER = logging.getLogger(__name__)


def _variable(script: str, name: str) -> str | None:
    match = re.search(rf"\bvar {name}\s*=\s*(\"[^\"]*\"|\w+)", script)
    return match.group(1).strip('"') if match else None


class WirelessEntity(MultiscrapeEntity):
    """Base for entities that read the radio settings and change them."""

    _attr_has_entity_name = True
    _entity_id_format: str

    def __init__(
        self, hass: HomeAssistant, coordinator, scraper, client: GatewayClient, device_info, key: str, name: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(hass, coordinator, scraper, name, None, False, None, None, {})
        self._client = client
        self._attr_device_info = device_info
        self._attr_unique_id = f"xfinity_gateway_{key}"
        self._attr_translation_key = key
        self.entity_id = async_generate_entity_id(
            self._entity_id_format, entity_object_id(name), hass=hass
        )
        self._script_selector = Selector(
            hass, {CONF_NAME: name, CONF_SELECT: Template(WIRELESS_SCRIPT_SELECTOR, hass)}
        )
        self._script = ""

    def _update_sensor(self) -> None:
        """Keep the page's script for the radio/WPS variables."""
        try:
            self._script = self.scraper.scrape(
                self._script_selector, self._name, context=self.coordinator.scrape_context
            ) or ""
        except Exception as exception:  # noqa: BLE001 - mirrors multiscrape's own broad on-error handling
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to scrape %s: %s", self.scraper.name, self._name, exception
            )
            return
        self._update_state()

    def _update_state(self) -> None:
        raise NotImplementedError

    def radio(self, variable: str) -> bool | None:
        """Return whether a radio is on, from its script variable."""
        return {"true": True, "false": False}.get(_variable(self._script, variable))

    def radios(self) -> tuple[bool | None, ...]:
        """Return the (2.4 GHz, 5 GHz, 6 GHz) radio settings."""
        return tuple(self.radio(variable) for _, _, variable, _ in WIFI_RADIOS)

    async def async_set_radios(self, changes: dict[str, bool]) -> None:
        """Set radios by ssid_number, then refresh once the gateway has applied them."""
        wps_enabled = _variable(self._script, "G_wps_enabled") == "true"
        wps_method = _variable(self._script, "G_wps_method") or "PushButton"
        try:
            for ssid_number, on in changes.items():
                await self._client.async_set_radio(ssid_number, on, wps_enabled, wps_method)
        except GatewayError as err:
            raise HomeAssistantError(f"{self.name} failed: {err}") from err
        await asyncio.sleep(WIFI_SAVE_DELAY)
        await self.coordinator.async_request_refresh()
