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

The gateway has four separate status pages we scrape: network_setup.jst (the
original set of fields), connection_status.jst (LAN/Wi-Fi summary fields),
lan.jst (per-port LAN Ethernet status/speed/MAC) and wifi.jst (per-band Wi-Fi
MAC addresses). Rather than modify multiscrape's own coordinator (which only
ever fetches a single resource per cycle), this builds four independent
scraper/coordinator pairs, one per page - all sharing the same authenticated
HttpSession (and thus the same login/cookies) as the first, so this doesn't
multiply the login load on the gateway. Four independent multiscrape
coordinators, one shared session.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant

from custom_components.multiscrape.coordinator import (
    create_content_request_manager,
    create_multiscrape_coordinator,
)
from custom_components.multiscrape.file import create_file_manager
from custom_components.multiscrape.http_session import create_http_session
from custom_components.multiscrape.scraper import create_scraper

from .const import DOMAIN
from .util import (
    build_connection_status_conf,
    build_lan_conf,
    build_scraper_conf,
    build_wifi_conf,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
SCRAPER_CONFIG_NAME = "xfinity_gateway"
CONNECTION_STATUS_CONFIG_NAME = "xfinity_gateway_connection_status"
LAN_CONFIG_NAME = "xfinity_gateway_lan"
WIFI_CONFIG_NAME = "xfinity_gateway_wifi"


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
    # Do NOT call coordinator.async_register_shutdown() here - that's only for
    # coordinators created outside a config entry context (which is what
    # multiscrape itself uses it for, in its own YAML-only _async_process_config).
    # HA core detects we're inside async_setup_entry and wires up this
    # coordinator's shutdown to the config entry automatically; calling it
    # manually raises RuntimeError("This should only be used outside of
    # config entries.").
    await coordinator.async_config_entry_first_refresh()

    # Second page (connection_status.jst), same session - see module docstring.
    connection_status_conf = build_connection_status_conf(
        conf, scraper_conf[CONF_SCAN_INTERVAL]
    )
    scraper_connection_status = create_scraper(
        CONNECTION_STATUS_CONFIG_NAME, connection_status_conf, hass, file_manager
    )
    request_manager_connection_status = create_content_request_manager(
        CONNECTION_STATUS_CONFIG_NAME, connection_status_conf, hass, session
    )
    coordinator_connection_status = create_multiscrape_coordinator(
        CONNECTION_STATUS_CONFIG_NAME,
        connection_status_conf,
        hass,
        request_manager_connection_status,
        file_manager,
        scraper_connection_status,
    )
    await coordinator_connection_status.async_config_entry_first_refresh()

    # Third page (lan.jst), same shared session.
    lan_conf = build_lan_conf(conf, scraper_conf[CONF_SCAN_INTERVAL])
    scraper_lan = create_scraper(LAN_CONFIG_NAME, lan_conf, hass, file_manager)
    request_manager_lan = create_content_request_manager(
        LAN_CONFIG_NAME, lan_conf, hass, session
    )
    coordinator_lan = create_multiscrape_coordinator(
        LAN_CONFIG_NAME, lan_conf, hass, request_manager_lan, file_manager, scraper_lan
    )
    await coordinator_lan.async_config_entry_first_refresh()

    # Fourth page (wifi.jst), same shared session.
    wifi_conf = build_wifi_conf(conf, scraper_conf[CONF_SCAN_INTERVAL])
    scraper_wifi = create_scraper(WIFI_CONFIG_NAME, wifi_conf, hass, file_manager)
    request_manager_wifi = create_content_request_manager(
        WIFI_CONFIG_NAME, wifi_conf, hass, session
    )
    coordinator_wifi = create_multiscrape_coordinator(
        WIFI_CONFIG_NAME, wifi_conf, hass, request_manager_wifi, file_manager, scraper_wifi
    )
    await coordinator_wifi.async_config_entry_first_refresh()

    async def _shutdown_session(_event, _session=session):
        await _session.async_close()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown_session)
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "scraper": scraper,
        "coordinator_connection_status": coordinator_connection_status,
        "scraper_connection_status": scraper_connection_status,
        "coordinator_lan": coordinator_lan,
        "scraper_lan": scraper_lan,
        "coordinator_wifi": coordinator_wifi,
        "scraper_wifi": scraper_wifi,
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
