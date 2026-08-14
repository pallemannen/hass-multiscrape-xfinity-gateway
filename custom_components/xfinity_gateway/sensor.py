"""Sensors for the Xfinity Gateway integration.

Reuses multiscrape's MultiscrapeEntity (coordinator/availability plumbing)
and Selector (CSS-selector + value_template evaluation) directly, so each
sensor is just "which field, which selector" - the scraping engine itself
is entirely multiscrape's.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_VALUE_TEMPLATE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util

from custom_components.multiscrape.const import CONF_SELECT as MS_CONF_SELECT
from custom_components.multiscrape.entity import MultiscrapeEntity
from custom_components.multiscrape.selector import Selector

from .const import (
    CURRENT_TIME_FIELD_KEY,
    CURRENT_TIME_FORMAT,
    DOMAIN,
    FIELDS,
    SYSTEM_UPTIME_FIELD_KEY,
    VALUE_TEMPLATE_STRIP,
    GatewayField,
)

_LOGGER = logging.getLogger(__name__)
ENTITY_ID_FORMAT = "sensor.{}"

# Format verified against a real gateway (see this repo's previous manual
# Template Helper instructions): "<n> day(s) <n>h:<n>m:<n>s", e.g.
# "5 day(s) 3h:12m:45s". Mirrors that same regex_findall-based parsing.
_DAYS_RE = re.compile(r"(?P<days>\d+)\s*day", re.IGNORECASE)
_HOURS_RE = re.compile(r"(?P<h>\d+)h:")
_MINUTES_RE = re.compile(r"(?P<m>\d+)m:")
_SECONDS_RE = re.compile(r"(?P<s>\d+)s")


def _parse_uptime(text: str | None) -> timedelta | None:
    """Parse a gateway uptime string into a timedelta."""
    if not text:
        return None

    days_match = _DAYS_RE.search(text)
    hours_match = _HOURS_RE.search(text)
    minutes_match = _MINUTES_RE.search(text)
    seconds_match = _SECONDS_RE.search(text)

    if not (hours_match or minutes_match or seconds_match):
        return None

    return timedelta(
        days=int(days_match.group("days")) if days_match else 0,
        hours=int(hours_match.group("h")) if hours_match else 0,
        minutes=int(minutes_match.group("m")) if minutes_match else 0,
        seconds=int(seconds_match.group("s")) if seconds_match else 0,
    )


def _build_selector(hass: HomeAssistant, name: str, select: str) -> Selector:
    return Selector(
        hass,
        {
            CONF_NAME: name,
            MS_CONF_SELECT: Template(select, hass),
            CONF_VALUE_TEMPLATE: Template(VALUE_TEMPLATE_STRIP, hass),
        },
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xfinity Gateway sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    scraper = data["scraper"]

    entities: list[SensorEntity] = [
        GatewayFieldSensor(hass, coordinator, scraper, field) for field in FIELDS
    ]
    entities.append(LastRebootSensor(hass, coordinator, scraper))

    async_add_entities(entities)


class GatewayFieldSensor(MultiscrapeEntity, SensorEntity):
    """A sensor reading a single field off the gateway status page."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator,
        scraper,
        field: GatewayField,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, scraper, field.name, None, False, None, None, {})

        self._attr_unique_id = f"xfinity_gateway_{field.key}"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        self._selector = _build_selector(hass, field.name, field.select)

    def _update_sensor(self) -> None:
        """Update state from the scraper data."""
        try:
            self._attr_native_value = self.scraper.scrape(
                self._selector, self._name, context=self.coordinator.scrape_context
            )
        except Exception as exception:  # noqa: BLE001 - mirrors multiscrape's own broad on-error handling
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to scrape %s: %s", self.scraper.name, self._name, exception
            )


class LastRebootSensor(MultiscrapeEntity, SensorEntity):
    """Derived timestamp sensor: the gateway's own reported current time minus its
    reported system uptime.

    Deliberately anchored to the gateway's own clock (its "Current Time" field)
    rather than Home Assistant's utcnow() - this mirrors the previously-validated
    manual Template Helper this integration replaces, and avoids drift if the
    gateway's clock and HA's clock disagree.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, hass: HomeAssistant, coordinator, scraper) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, scraper, "Last Reboot", None, False, None, None, {})

        self._attr_unique_id = "xfinity_gateway_last_reboot"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        current_time_field = next(f for f in FIELDS if f.key == CURRENT_TIME_FIELD_KEY)
        uptime_field = next(f for f in FIELDS if f.key == SYSTEM_UPTIME_FIELD_KEY)
        self._current_time_selector = _build_selector(
            hass, current_time_field.name, current_time_field.select
        )
        self._uptime_selector = _build_selector(hass, uptime_field.name, uptime_field.select)

    def _update_sensor(self) -> None:
        """Update state from the scraper data."""
        try:
            raw_current_time = self.scraper.scrape(
                self._current_time_selector, self._name, context=self.coordinator.scrape_context
            )
            raw_uptime = self.scraper.scrape(
                self._uptime_selector, self._name, context=self.coordinator.scrape_context
            )
            duration = _parse_uptime(raw_uptime)
        except Exception as exception:  # noqa: BLE001
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to compute last reboot time: %s", self.scraper.name, exception
            )
            return

        if duration is None:
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Could not parse uptime string %r into a duration; the "
                "gateway's uptime format may differ from what this "
                "integration expects - please open an issue with the raw value.",
                self.scraper.name,
                raw_uptime,
            )
            return

        try:
            naive_current_time = datetime.strptime(raw_current_time, CURRENT_TIME_FORMAT)
        except (TypeError, ValueError) as exception:
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Could not parse gateway current time %r (expected format %s): %s",
                self.scraper.name,
                raw_current_time,
                CURRENT_TIME_FORMAT,
                exception,
            )
            return

        gateway_now = naive_current_time.replace(tzinfo=dt_util.now().tzinfo)
        self._attr_native_value = gateway_now - duration
