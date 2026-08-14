"""The Xfinity Gateway integration.

Depends on the multiscrape integration (domain: multiscrape) and reuses its
HTTP session / form-authentication / scraper / coordinator building blocks
directly (custom_components.multiscrape.*), instead of reimplementing the
form-login-and-scrape logic here.

multiscrape itself only parses its own `multiscrape:` YAML key once, at HA
startup, and has no runtime API to hand it a scraper config afterwards - so
rather than trying to feed config into multiscrape's own config, this builds
one scraper/coordinator using the same non-underscore factory functions
multiscrape uses on itself (see multiscrape/__init__.py's
_async_process_config), and then forwards setup to the sensor/binary_sensor
platforms via the config entry, the same way any other config-flow
integration does.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant

from custom_components.multiscrape.coordinator import (
    create_content_request_manager,
    create_multiscrape_coordinator,
)
from custom_components.multiscrape.file import create_file_manager
from custom_components.multiscrape.http_session import create_http_session
from custom_components.multiscrape.scraper import create_scraper

from .const import DOMAIN
from .util import build_scraper_conf

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
SCRAPER_CONFIG_NAME = "xfinity_gateway"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Xfinity Gateway from a config entry."""
    conf = entry.data
    scraper_conf = build_scraper_conf(conf)

    file_manager = await create_file_manager(hass, SCRAPER_CONFIG_NAME, False)
    session = create_http_session(SCRAPER_CONFIG_NAME, scraper_conf, hass, file_manager)
    scraper = create_scraper(SCRAPER_CONFIG_NAME, scraper_conf, hass, file_manager)
    request_manager = create_content_request_manager(
        SCRAPER_CONFIG_NAME, scraper_conf, hass, session
    )
    coordinator = create_multiscrape_coordinator(
        SCRAPER_CONFIG_NAME, scraper_conf, hass, request_manager, file_manager, scraper
    )
    await coordinator.async_register_shutdown()
    await coordinator.async_config_entry_first_refresh()

    async def _shutdown_session(_event, _session=session):
        await _session.async_close()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown_session)
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "scraper": scraper,
        "session": session,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["session"].async_close()
    return unload_ok
