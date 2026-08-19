"""Shared device info for the Xfinity Gateway integration.

Built once per config entry (in __init__.py) by directly scraping the
already-fetched network_setup.jst page for the gateway's own identity
fields, and attached to every entity in sensor.py/binary_sensor.py so they
all group under one device instead of appearing as ungrouped entities.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_HOST, CONF_NAME, DEFAULT_NAME, DOMAIN, FIELDS
from .util import build_selector


def build_device_info(hass: HomeAssistant, entry: ConfigEntry, coordinator, scraper) -> DeviceInfo:
    """Build the device info shared by every entity in this config entry."""

    def field(key: str) -> str | None:
        gateway_field = next(f for f in FIELDS if f.key == key)
        selector = build_selector(hass, gateway_field.name, gateway_field.select)
        try:
            return scraper.scrape(
                selector, gateway_field.name, context=coordinator.scrape_context
            )
        except Exception:  # noqa: BLE001 - device info is best-effort, never block setup
            return None

    host = entry.data[CONF_HOST]
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_NAME, DEFAULT_NAME),
        manufacturer=field("manufacturer") or "Xfinity",
        model=field("model_number"),
        sw_version=field("software_version"),
        serial_number=field("serial_number"),
        configuration_url=f"http://{host}/",
    )
