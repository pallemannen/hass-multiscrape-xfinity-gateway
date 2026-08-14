"""The Xfinity Gateway integration.

Depends on the multiscrape integration (domain: multiscrape) and reuses its
HTTP session / form-authentication / scraper / coordinator building blocks
directly (custom_components.multiscrape.*), instead of reimplementing the
form-login-and-scrape logic here.

multiscrape itself only parses its own `multiscrape:` YAML key once, at HA
startup, and has no runtime API to hand it a scraper config afterwards - so
rather than trying to feed YAML into multiscrape's own config, this builds
one scraper/coordinator using the same non-underscore factory functions
multiscrape uses on itself (see multiscrape/__init__.py's
_async_process_config), and then dispatches sensor/binary_sensor setup via
discovery.async_load_platform the same way multiscrape does.
"""
from __future__ import annotations

import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_RESOURCE,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.typing import ConfigType

from custom_components.multiscrape.const import (
    CONF_FORM_INPUT,
    CONF_FORM_RESUBMIT_ERROR,
    CONF_FORM_SELECT,
    CONF_FORM_SUBMIT,
    CONF_FORM_SUBMIT_ONCE,
    CONF_PARSER,
    DEFAULT_PARSER,
)
from custom_components.multiscrape.coordinator import (
    create_content_request_manager,
    create_multiscrape_coordinator,
)
from custom_components.multiscrape.file import create_file_manager
from custom_components.multiscrape.http_session import create_http_session
from custom_components.multiscrape.scraper import create_scraper

from .const import DEFAULT_HOST, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
SCRAPER_CONFIG_NAME = "xfinity_gateway"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
                ): cv.time_period,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def _build_scraper_conf(conf: ConfigType) -> ConfigType:
    """Build a multiscrape-shaped scraper config for the gateway status page."""
    host = conf[CONF_HOST]
    return {
        CONF_RESOURCE: f"http://{host}/network_setup.jst",
        CONF_SCAN_INTERVAL: conf[CONF_SCAN_INTERVAL],
        CONF_PARSER: DEFAULT_PARSER,
        CONF_FORM_SUBMIT: {
            CONF_RESOURCE: f"http://{host}/",
            CONF_FORM_SELECT: "#pageForm",
            CONF_FORM_INPUT: {
                CONF_USERNAME: conf[CONF_USERNAME],
                CONF_PASSWORD: conf[CONF_PASSWORD],
            },
            CONF_FORM_SUBMIT_ONCE: True,
            CONF_FORM_RESUBMIT_ERROR: True,
        },
    }


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Xfinity Gateway integration."""
    conf = config[DOMAIN]
    scraper_conf = _build_scraper_conf(conf)

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

    async def _shutdown_session(_event, _session=session):
        await _session.async_close()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown_session)

    hass.data[DOMAIN] = {"coordinator": coordinator, "scraper": scraper}

    for platform in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(hass, platform, DOMAIN, {}, config)
        )

    return True
