"""Shared helpers for the Xfinity Gateway integration."""
from __future__ import annotations

import re
from datetime import timedelta

from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_RESOURCE,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VALUE_TEMPLATE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.helpers.typing import ConfigType

from custom_components.multiscrape.const import (
    CONF_FORM_INPUT,
    CONF_FORM_RESUBMIT_ERROR,
    CONF_FORM_SELECT,
    CONF_FORM_SUBMIT,
    CONF_FORM_SUBMIT_ONCE,
    CONF_PARSER,
    CONF_SEPARATOR,
    DEFAULT_PARSER,
    DEFAULT_SEPARATOR,
)
from custom_components.multiscrape.const import CONF_SELECT as MS_CONF_SELECT
from custom_components.multiscrape.const import CONF_SELECT_LIST
from custom_components.multiscrape.selector import Selector

from .const import VALUE_TEMPLATE_STRIP, WIRELESS_PATH


def build_scraper_conf(conf: ConfigType) -> ConfigType:
    """Build a multiscrape-shaped scraper config for the gateway status page.

    `conf` is a config entry's `data` dict: host, username, password, and
    scan_interval (plain int seconds, as stored by the config flow).
    """
    host = conf[CONF_HOST]
    return {
        CONF_RESOURCE: f"http://{host}/network_setup.jst",
        CONF_SCAN_INTERVAL: timedelta(seconds=conf[CONF_SCAN_INTERVAL]),
        CONF_PARSER: DEFAULT_PARSER,
        CONF_SEPARATOR: DEFAULT_SEPARATOR,
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


def build_connection_status_conf(conf: ConfigType, scan_interval: timedelta) -> ConfigType:
    """Build a minimal multiscrape-shaped conf for fetching connection_status.jst.

    No form_submit block needed here - this page is fetched through the same
    HttpSession (and thus the same cookies/login) already established for
    network_setup.jst, so authentication is already handled; this only needs
    enough config for create_scraper/create_content_request_manager/
    create_multiscrape_coordinator to know what URL and parser to use.
    """
    host = conf[CONF_HOST]
    return {
        CONF_RESOURCE: f"http://{host}/connection_status.jst",
        CONF_SCAN_INTERVAL: scan_interval,
        CONF_PARSER: DEFAULT_PARSER,
    }


def build_lan_conf(conf: ConfigType, scan_interval: timedelta) -> ConfigType:
    """Build a minimal multiscrape-shaped conf for fetching lan.jst.

    Same reasoning as build_connection_status_conf: fetched through the
    already-authenticated shared HttpSession, no form_submit needed.
    """
    host = conf[CONF_HOST]
    return {
        CONF_RESOURCE: f"http://{host}/lan.jst",
        CONF_SCAN_INTERVAL: scan_interval,
        CONF_PARSER: DEFAULT_PARSER,
    }


def build_wifi_conf(conf: ConfigType, scan_interval: timedelta) -> ConfigType:
    """Build a minimal multiscrape-shaped conf for fetching wifi.jst.

    Same reasoning as build_connection_status_conf: fetched through the
    already-authenticated shared HttpSession, no form_submit needed.
    """
    host = conf[CONF_HOST]
    return {
        CONF_RESOURCE: f"http://{host}/wifi.jst",
        CONF_SCAN_INTERVAL: scan_interval,
        CONF_PARSER: DEFAULT_PARSER,
    }


def build_hardware_conf(conf: ConfigType, scan_interval: timedelta) -> ConfigType:
    """Build a minimal multiscrape-shaped conf for fetching hardware.jst.

    Same reasoning as build_connection_status_conf: fetched through the
    already-authenticated shared HttpSession, no form_submit needed.
    """
    host = conf[CONF_HOST]
    return {
        CONF_RESOURCE: f"http://{host}/hardware.jst",
        CONF_SCAN_INTERVAL: scan_interval,
        CONF_PARSER: DEFAULT_PARSER,
    }


def build_wireless_conf(conf: ConfigType, scan_interval: timedelta) -> ConfigType:
    """Build a minimal multiscrape-shaped conf for fetching wireless_network_configuration.jst.

    Same reasoning as build_connection_status_conf: fetched through the
    already-authenticated shared HttpSession, no form_submit needed.
    """
    host = conf[CONF_HOST]
    return {
        CONF_RESOURCE: f"http://{host}/{WIRELESS_PATH}",
        CONF_SCAN_INTERVAL: scan_interval,
        CONF_PARSER: DEFAULT_PARSER,
    }


def build_selector(hass: HomeAssistant, name: str, select: str) -> Selector:
    """Build a multiscrape Selector for a single CSS-selected, stripped-text field."""
    return Selector(
        hass,
        {
            CONF_NAME: name,
            MS_CONF_SELECT: Template(select, hass),
            CONF_VALUE_TEMPLATE: Template(VALUE_TEMPLATE_STRIP, hass),
        },
    )


def build_list_selector(hass: HomeAssistant, name: str, select: str) -> Selector:
    """Build a multiscrape Selector returning every match's text, comma-separated."""
    return Selector(hass, {CONF_NAME: name, CONF_SELECT_LIST: Template(select, hass)})


# Entity IDs follow the entity name (shared rule with the AT&T Gateway
# integration), except that "Wi-Fi 2.4 GHz" becomes "wifi_24ghz" etc.
_WIFI_BANDS = (("Wi-Fi 2.4 GHz", "wifi_24ghz"), ("Wi-Fi 5 GHz", "wifi_5ghz"), ("Wi-Fi 6 GHz", "wifi_6ghz"))


def entity_object_id(name: str) -> str:
    """Return the entity ID object id (without domain) for an entity name."""
    for band, replacement in _WIFI_BANDS:
        name = name.replace(band, replacement)
    name = name.replace("Wi-Fi", "wifi")
    return "xfinity_gateway_" + re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", name.lower())).strip("_")
