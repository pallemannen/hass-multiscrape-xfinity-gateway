"""Binary sensor for the Xfinity Gateway integration."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_VALUE_TEMPLATE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.template import Template

from custom_components.multiscrape.const import CONF_SELECT as MS_CONF_SELECT
from custom_components.multiscrape.entity import MultiscrapeEntity
from custom_components.multiscrape.selector import Selector

from .const import CONNECTION_STATUS_FIELD_KEY, DOMAIN, FIELDS, VALUE_TEMPLATE_STRIP

_LOGGER = logging.getLogger(__name__)
ENTITY_ID_FORMAT = "binary_sensor.{}"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xfinity Gateway binary sensor from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    scraper = data["scraper"]

    async_add_entities([GatewayConnectivitySensor(hass, coordinator, scraper)])


class GatewayConnectivitySensor(MultiscrapeEntity, BinarySensorEntity):
    """Derived connectivity sensor: on when the scraped connection status is 'active'.

    'active' (not 'connected') is the verified value on a real gateway - see
    this repo's previous manual Template Helper instructions in the README.
    """

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, hass: HomeAssistant, coordinator, scraper) -> None:
        """Initialize the sensor."""
        super().__init__(
            hass, coordinator, scraper, "Connectivity", None, False, None, None, {}
        )

        self._attr_unique_id = "xfinity_gateway_connectivity"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        status_field = next(f for f in FIELDS if f.key == CONNECTION_STATUS_FIELD_KEY)
        self._selector = Selector(
            hass,
            {
                CONF_NAME: status_field.name,
                MS_CONF_SELECT: Template(status_field.select, hass),
                CONF_VALUE_TEMPLATE: Template(VALUE_TEMPLATE_STRIP, hass),
            },
        )

    def _update_sensor(self) -> None:
        """Update state from the scraper data."""
        try:
            value = self.scraper.scrape(
                self._selector, self._name, context=self.coordinator.scrape_context
            )
            self._attr_is_on = bool(value) and value.strip().lower() == "active"
        except Exception as exception:  # noqa: BLE001 - mirrors multiscrape's own broad on-error handling
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to scrape %s: %s", self.scraper.name, self._name, exception
            )
