"""Shared helpers for the Xfinity Gateway integration."""
from __future__ import annotations

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
    DEFAULT_PARSER,
)
from custom_components.multiscrape.const import CONF_SELECT as MS_CONF_SELECT
from custom_components.multiscrape.selector import Selector

from .const import VALUE_TEMPLATE_STRIP


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
