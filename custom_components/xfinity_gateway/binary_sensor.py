"""Binary sensors for the Xfinity Gateway integration."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.multiscrape.entity import MultiscrapeEntity

from .const import (
    BRIDGE_MESSAGE_FIELD_KEY,
    CONNECTION_STATUS_FIELD_KEY,
    CONNECTION_STATUS_FIELDS,
    DHCP_CLIENT_IPV4_FIELD_KEY,
    DHCP_CLIENT_IPV6_FIELD_KEY,
    DOMAIN,
    FIELDS,
    ICON_ACTIVE,
    ICON_BRIDGE,
    ICON_DHCP,
    ICON_INACTIVE,
    ICON_WIFI_OFF,
    ICON_WIFI_ON,
    LAN_DHCP_SERVER_STATUS_FIELD_KEY,
    WIFI_24GHZ_STATUS_FIELD_KEY,
    WIFI_5GHZ_STATUS_FIELD_KEY,
    WIFI_6GHZ_STATUS_FIELD_KEY,
)
from .util import build_selector

_LOGGER = logging.getLogger(__name__)
ENTITY_ID_FORMAT = "binary_sensor.{}"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xfinity Gateway binary sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    scraper = data["scraper"]
    coordinator_cs = data["coordinator_connection_status"]
    scraper_cs = data["scraper_connection_status"]

    dhcp_client_ipv4_field = next(f for f in FIELDS if f.key == DHCP_CLIENT_IPV4_FIELD_KEY)
    dhcp_client_ipv6_field = next(f for f in FIELDS if f.key == DHCP_CLIENT_IPV6_FIELD_KEY)
    dhcp_server_field = next(
        f for f in CONNECTION_STATUS_FIELDS if f.key == LAN_DHCP_SERVER_STATUS_FIELD_KEY
    )

    async_add_entities(
        [
            GatewayConnectivitySensor(hass, coordinator, scraper),
            GatewayEnabledDisabledSensor(
                hass,
                coordinator,
                scraper,
                "DHCP Client",
                "dhcp_client",
                ICON_DHCP,
                dhcp_client_ipv4_field.name,
                dhcp_client_ipv4_field.select,
            ),
            GatewayEnabledDisabledSensor(
                hass,
                coordinator,
                scraper,
                "DHCPv6 Client",
                "dhcpv6_client",
                ICON_DHCP,
                dhcp_client_ipv6_field.name,
                dhcp_client_ipv6_field.select,
            ),
            GatewayEnabledDisabledSensor(
                hass,
                coordinator_cs,
                scraper_cs,
                "DHCP Server",
                "dhcp_server",
                ICON_DHCP,
                dhcp_server_field.name,
                dhcp_server_field.select,
            ),
            GatewayBridgeModeSensor(hass, coordinator, scraper),
            GatewayWifiSensor(hass, coordinator_cs, scraper_cs),
        ]
    )


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
        self._attr_icon = ICON_INACTIVE
        status_field = next(f for f in FIELDS if f.key == CONNECTION_STATUS_FIELD_KEY)
        self._selector = build_selector(hass, status_field.name, status_field.select)

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
            return

        self._attr_icon = ICON_ACTIVE if self._attr_is_on else ICON_INACTIVE


class GatewayEnabledDisabledSensor(MultiscrapeEntity, BinarySensorEntity):
    """Generic binary sensor: on when a scraped field's value is 'enabled'.

    No built-in HA device_class renders exactly "Enabled"/"Disabled" (the
    closest, `running`, says "Running"/"Not running") - so this uses a
    translation_key instead to get that custom wording, rather than force a
    mismatched device_class just to reuse its built-in strings. See
    strings.json / translations/en.json's entity.binary_sensor.enabled_disabled.
    """

    _attr_translation_key = "enabled_disabled"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator,
        scraper,
        name: str,
        unique_id_suffix: str,
        icon: str,
        field_name: str,
        field_select: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, scraper, name, None, False, None, None, {})

        self._attr_icon = icon
        self._attr_unique_id = f"xfinity_gateway_{unique_id_suffix}"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        self._selector = build_selector(hass, field_name, field_select)

    def _update_sensor(self) -> None:
        """Update state from the scraper data."""
        try:
            value = self.scraper.scrape(
                self._selector, self._name, context=self.coordinator.scrape_context
            )
            self._attr_is_on = bool(value) and value.strip().lower() == "enabled"
        except Exception as exception:  # noqa: BLE001 - mirrors multiscrape's own broad on-error handling
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to scrape %s: %s", self.scraper.name, self._name, exception
            )


class GatewayBridgeModeSensor(MultiscrapeEntity, BinarySensorEntity):
    """Derived sensor: on when the Bridge Message reports being in bridge mode.

    Not "enabled/disabled" wording like GatewayEnabledDisabledSensor - "mode"
    reads oddly that way, so this gets its own translation_key with wording
    that actually fits (see strings.json's entity.binary_sensor.bridge_mode).
    """

    _attr_translation_key = "bridge_mode"

    def __init__(self, hass: HomeAssistant, coordinator, scraper) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, scraper, "Bridge Mode", None, False, None, None, {})

        self._attr_icon = ICON_BRIDGE
        self._attr_unique_id = "xfinity_gateway_bridge_mode"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        message_field = next(f for f in FIELDS if f.key == BRIDGE_MESSAGE_FIELD_KEY)
        self._selector = build_selector(hass, message_field.name, message_field.select)

    def _update_sensor(self) -> None:
        """Update state from the scraper data."""
        try:
            value = self.scraper.scrape(
                self._selector, self._name, context=self.coordinator.scrape_context
            )
            self._attr_is_on = bool(value) and "in bridge mode" in value.strip().lower()
        except Exception as exception:  # noqa: BLE001 - mirrors multiscrape's own broad on-error handling
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to scrape %s: %s", self.scraper.name, self._name, exception
            )


class GatewayWifiSensor(MultiscrapeEntity, BinarySensorEntity):
    """Derived sensor: on when any Wi-Fi band (2.4/5/6 GHz) is not 'Inactive'.

    Uses standard on/off wording (no translation_key) - "Enabled"/"Disabled"
    doesn't fit "WiFi" as a whole the way it fits a single DHCP toggle. Icon
    switches between wifi/wifi-off instead, mirroring the Connectivity /
    Connection Status state-dependent icon pattern in sensor.py.
    """

    def __init__(self, hass: HomeAssistant, coordinator, scraper) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, scraper, "WiFi", None, False, None, None, {})

        self._attr_icon = ICON_WIFI_OFF
        self._attr_unique_id = "xfinity_gateway_wifi"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        band_keys = (
            WIFI_24GHZ_STATUS_FIELD_KEY,
            WIFI_5GHZ_STATUS_FIELD_KEY,
            WIFI_6GHZ_STATUS_FIELD_KEY,
        )
        self._selectors = [
            build_selector(hass, band_field.name, band_field.select)
            for key in band_keys
            for band_field in CONNECTION_STATUS_FIELDS
            if band_field.key == key
        ]

    def _update_sensor(self) -> None:
        """Update state from the scraper data."""
        try:
            any_active = False
            for selector in self._selectors:
                value = self.scraper.scrape(
                    selector, self._name, context=self.coordinator.scrape_context
                )
                if value and value.strip().lower() != "inactive":
                    any_active = True
            self._attr_is_on = any_active
        except Exception as exception:  # noqa: BLE001 - mirrors multiscrape's own broad on-error handling
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to scrape %s: %s", self.scraper.name, self._name, exception
            )
            return

        self._attr_icon = ICON_WIFI_ON if self._attr_is_on else ICON_WIFI_OFF
