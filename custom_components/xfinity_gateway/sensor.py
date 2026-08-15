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

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from custom_components.multiscrape.entity import MultiscrapeEntity

from .const import (
    BRIDGE_MESSAGE_FIELD_KEY,
    CONNECTION_STATUS_FIELD_KEY,
    CONNECTION_STATUS_FIELDS,
    CURRENT_TIME_FIELD_KEY,
    CURRENT_TIME_FORMAT,
    DOMAIN,
    FIELDS,
    ICON_ACTIVE,
    ICON_BRIDGE,
    ICON_INACTIVE,
    ICON_LAN_SPEED,
    ICON_MAC_ADDRESS,
    ICON_ROUTER,
    LAN_1_SPEED_FIELD_KEY,
    LAN_2_SPEED_FIELD_KEY,
    LAN_3_SPEED_FIELD_KEY,
    LAN_4_SPEED_FIELD_KEY,
    LAN_FIELDS,
    LAN_MAC_ADDRESS_FIELD_KEY,
    LAST_REBOOT_ICON,
    STATIC_ICONS,
    SYSTEM_UPTIME_FIELD_KEY,
    WIFI_24GHZ_CLIENT_COUNT_FIELD_KEY,
    WIFI_24GHZ_MAC_ADDRESS_FIELD_KEY,
    WIFI_5GHZ_CLIENT_COUNT_FIELD_KEY,
    WIFI_5GHZ_MAC_ADDRESS_FIELD_KEY,
    WIFI_6GHZ_CLIENT_COUNT_FIELD_KEY,
    WIFI_6GHZ_MAC_ADDRESS_FIELD_KEY,
    WIFI_CLIENT_COUNT_ICON,
    WIFI_MAC_FIELDS,
    WIFI_STATUS_FIELD_KEYS,
    ICON_WIFI_ACTIVE,
    ICON_WIFI_INACTIVE,
    ConnectionStatusField,
    GatewayField,
)
from .util import build_selector

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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xfinity Gateway sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    scraper = data["scraper"]
    coordinator_cs = data["coordinator_connection_status"]
    scraper_cs = data["scraper_connection_status"]
    coordinator_lan = data["coordinator_lan"]
    scraper_lan = data["scraper_lan"]
    coordinator_wifi = data["coordinator_wifi"]
    scraper_wifi = data["scraper_wifi"]

    entities: list[SensorEntity] = [
        GatewayFieldSensor(hass, coordinator, scraper, field) for field in FIELDS
    ]
    entities.append(LastRebootSensor(hass, coordinator, scraper))
    entities.append(ModeSensor(hass, coordinator, scraper))

    for field in CONNECTION_STATUS_FIELDS:
        entity_cls = NumericGatewayFieldSensor if field.numeric else GatewayFieldSensor
        entities.append(entity_cls(hass, coordinator_cs, scraper_cs, field))

    entities.append(WifiClientCountSensor(hass, coordinator_cs, scraper_cs))

    entities.extend(
        GatewayFieldSensor(hass, coordinator_lan, scraper_lan, field) for field in LAN_FIELDS
    )
    entities.extend(
        GatewayFieldSensor(hass, coordinator_wifi, scraper_wifi, field)
        for field in WIFI_MAC_FIELDS
    )
    entities.append(LanSpeedSensor(hass, coordinator_lan, scraper_lan))
    entities.append(
        MacAddressSensor(hass, coordinator_lan, scraper_lan, coordinator_wifi, scraper_wifi)
    )

    async_add_entities(entities)


class GatewayFieldSensor(MultiscrapeEntity, SensorEntity):
    """A sensor reading a single field off a gateway status page.

    Works for either GatewayField (network_setup.jst) or ConnectionStatusField
    (connection_status.jst) - both just carry key/name/select.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator,
        scraper,
        field: GatewayField | ConnectionStatusField,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, scraper, field.name, None, False, None, None, {})

        self._attr_unique_id = f"xfinity_gateway_{field.key}"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        self._field_key = field.key
        self._attr_icon = STATIC_ICONS.get(
            field.key,
            ICON_INACTIVE
            if field.key == CONNECTION_STATUS_FIELD_KEY
            else ICON_WIFI_INACTIVE
            if field.key in WIFI_STATUS_FIELD_KEYS
            else None,
        )
        self._selector = build_selector(hass, field.name, field.select)

    def _update_sensor(self) -> None:
        """Update state from the scraper data."""
        try:
            value = self.scraper.scrape(
                self._selector, self._name, context=self.coordinator.scrape_context
            )
        except Exception as exception:  # noqa: BLE001 - mirrors multiscrape's own broad on-error handling
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to scrape %s: %s", self.scraper.name, self._name, exception
            )
            return

        self._attr_native_value = value
        if self._field_key == CONNECTION_STATUS_FIELD_KEY:
            self._attr_icon = ICON_ACTIVE if value == "Active" else ICON_INACTIVE
        elif self._field_key in WIFI_STATUS_FIELD_KEYS:
            self._attr_icon = ICON_WIFI_ACTIVE if value == "Active" else ICON_WIFI_INACTIVE


class NumericGatewayFieldSensor(GatewayFieldSensor):
    """A GatewayFieldSensor whose value is a plain integer count (e.g. client counts).

    No built-in HA sensor device_class fits a plain count like this - left
    unset, with state_class=measurement so it still gets history/graphing.
    """

    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _update_sensor(self) -> None:
        """Update state from the scraper data, parsed as an int."""
        try:
            raw_value = self.scraper.scrape(
                self._selector, self._name, context=self.coordinator.scrape_context
            )
        except Exception as exception:  # noqa: BLE001
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to scrape %s: %s", self.scraper.name, self._name, exception
            )
            return

        try:
            # value_template's `parse_result=True` rendering already turns a
            # bare numeric string like "0" into a native Python int before it
            # gets here, so raw_value isn't reliably a str - str() first
            # makes int(str(x).strip()) work whether it's already an int
            # or still text.
            self._attr_native_value = int(str(raw_value).strip())
        except (TypeError, ValueError) as exception:
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Could not parse %s as an integer (raw value %r): %s",
                self.scraper.name,
                self._name,
                raw_value,
                exception,
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

        self._attr_icon = LAST_REBOOT_ICON
        self._attr_unique_id = "xfinity_gateway_last_reboot"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        current_time_field = next(f for f in FIELDS if f.key == CURRENT_TIME_FIELD_KEY)
        uptime_field = next(f for f in FIELDS if f.key == SYSTEM_UPTIME_FIELD_KEY)
        self._current_time_selector = build_selector(
            hass, current_time_field.name, current_time_field.select
        )
        self._uptime_selector = build_selector(hass, uptime_field.name, uptime_field.select)

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


class ModeSensor(MultiscrapeEntity, SensorEntity):
    """Derived sensor: 'Bridge' or 'Router', from the same Bridge Message field
    and detection text ("in bridge mode") as GatewayBridgeModeSensor's binary
    sensor in binary_sensor.py - this just exposes it as a plain-text state
    (with a matching bridge/router icon) instead of on/off.
    """

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["Bridge", "Router"]

    def __init__(self, hass: HomeAssistant, coordinator, scraper) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, scraper, "Mode", None, False, None, None, {})

        self._attr_unique_id = "xfinity_gateway_mode"
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
        except Exception as exception:  # noqa: BLE001 - mirrors multiscrape's own broad on-error handling
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to scrape %s: %s", self.scraper.name, self._name, exception
            )
            return

        is_bridge = bool(value) and "in bridge mode" in value.strip().lower()
        self._attr_native_value = "Bridge" if is_bridge else "Router"
        self._attr_icon = ICON_BRIDGE if is_bridge else ICON_ROUTER


class WifiClientCountSensor(MultiscrapeEntity, SensorEntity):
    """Derived sensor: sum of the three per-band Wi-Fi client counts.

    Re-scrapes all three band selectors itself each cycle, the same way
    LastRebootSensor recomputes from its own source fields rather than
    reading other entities' states (fragile/order-dependent).
    """

    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass: HomeAssistant, coordinator, scraper) -> None:
        """Initialize the sensor."""
        super().__init__(
            hass, coordinator, scraper, "Number of WiFi Clients", None, False, None, None, {}
        )

        self._attr_icon = WIFI_CLIENT_COUNT_ICON
        self._attr_unique_id = "xfinity_gateway_wifi_client_count"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        band_keys = (
            WIFI_24GHZ_CLIENT_COUNT_FIELD_KEY,
            WIFI_5GHZ_CLIENT_COUNT_FIELD_KEY,
            WIFI_6GHZ_CLIENT_COUNT_FIELD_KEY,
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
            total = 0
            for selector in self._selectors:
                raw_value = self.scraper.scrape(
                    selector, self._name, context=self.coordinator.scrape_context
                )
                # See NumericGatewayFieldSensor._update_sensor for why str() first.
                total += int(str(raw_value).strip())
        except Exception as exception:  # noqa: BLE001
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to compute %s: %s", self.scraper.name, self._name, exception
            )
            return

        self._attr_native_value = total


_LEADING_INT_RE = re.compile(r"\d+")


class LanSpeedSensor(MultiscrapeEntity, SensorEntity):
    """Derived sensor: the highest of the four LAN ports' Connection Speed values.

    Re-scrapes all four speed fields itself each cycle (same pattern as
    WifiClientCountSensor/LastRebootSensor). Kept as the winning port's raw
    string (e.g. "1000 Mbps"), not a bare number, matching this integration's
    existing string-sensor style - only used numerically to pick the winner.
    """

    _attr_device_class = None

    def __init__(self, hass: HomeAssistant, coordinator, scraper) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, scraper, "LAN Speed", None, False, None, None, {})

        self._attr_icon = ICON_LAN_SPEED
        self._attr_unique_id = "xfinity_gateway_lan_speed"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        speed_keys = (
            LAN_1_SPEED_FIELD_KEY,
            LAN_2_SPEED_FIELD_KEY,
            LAN_3_SPEED_FIELD_KEY,
            LAN_4_SPEED_FIELD_KEY,
        )
        self._selectors = [
            build_selector(hass, field.name, field.select)
            for key in speed_keys
            for field in LAN_FIELDS
            if field.key == key
        ]

    def _update_sensor(self) -> None:
        """Update state from the scraper data."""
        try:
            raw_values = [
                self.scraper.scrape(
                    selector, self._name, context=self.coordinator.scrape_context
                )
                for selector in self._selectors
            ]
        except Exception as exception:  # noqa: BLE001
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to compute %s: %s", self.scraper.name, self._name, exception
            )
            return

        best_raw = raw_values[0]
        best_speed = -1
        for raw in raw_values:
            match = _LEADING_INT_RE.search(raw or "")
            speed = int(match.group()) if match else 0
            if speed > best_speed:
                best_speed = speed
                best_raw = raw

        self._attr_native_value = best_raw


class MacAddressSensor(MultiscrapeEntity, SensorEntity):
    """Derived sensor: the gateway's "effective" MAC address.

    Priority order: LAN, then Wi-Fi 2.4/5/6 GHz - the first one that scrapes
    to a non-empty value wins. Reads from two different pages/scrapers (LAN
    and Wi-Fi), so it subscribes to the LAN coordinator for update timing
    (both run on the same configured scan_interval) but also holds a direct
    reference to the Wi-Fi scraper to read from it too.
    """

    _attr_device_class = None

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator_lan,
        scraper_lan,
        coordinator_wifi,
        scraper_wifi,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            hass, coordinator_lan, scraper_lan, "MAC Address", None, False, None, None, {}
        )

        self._attr_icon = ICON_MAC_ADDRESS
        self._attr_unique_id = "xfinity_gateway_mac_address"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        self._scraper_wifi = scraper_wifi

        lan_mac_field = next(f for f in LAN_FIELDS if f.key == LAN_MAC_ADDRESS_FIELD_KEY)
        self._lan_selector = build_selector(hass, lan_mac_field.name, lan_mac_field.select)

        wifi_keys = (
            WIFI_24GHZ_MAC_ADDRESS_FIELD_KEY,
            WIFI_5GHZ_MAC_ADDRESS_FIELD_KEY,
            WIFI_6GHZ_MAC_ADDRESS_FIELD_KEY,
        )
        self._wifi_selectors = [
            build_selector(hass, field.name, field.select)
            for key in wifi_keys
            for field in WIFI_MAC_FIELDS
            if field.key == key
        ]

    def _update_sensor(self) -> None:
        """Update state from the scraper data."""
        try:
            candidates = [
                self.scraper.scrape(
                    self._lan_selector, self._name, context=self.coordinator.scrape_context
                )
            ]
            candidates.extend(
                self._scraper_wifi.scrape(selector, self._name)
                for selector in self._wifi_selectors
            )
        except Exception as exception:  # noqa: BLE001
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to compute %s: %s", self.scraper.name, self._name, exception
            )
            return

        for candidate in candidates:
            if candidate and candidate.strip():
                self._attr_native_value = candidate
                return
