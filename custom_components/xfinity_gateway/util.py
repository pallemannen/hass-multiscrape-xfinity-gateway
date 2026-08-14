"""Shared helpers for the Xfinity Gateway integration."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_RESOURCE,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
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
