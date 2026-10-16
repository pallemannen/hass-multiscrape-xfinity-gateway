"""Sensors for the Xfinity Gateway integration.

Reuses multiscrape's MultiscrapeEntity (coordinator/availability plumbing)
and Selector (CSS-selector + value_template evaluation) directly, so each
sensor is just "which field, which selector" - the scraping engine itself
is entirely multiscrape's.
"""
from __future__ import annotations

import logging
import re
import socket
from datetime import datetime, timedelta

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    PERCENTAGE,
    UnitOfDataRate,
    UnitOfFrequency,
    UnitOfInformation,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util


from .const import (
    CODEWORD_FIELDS,
    CONNECTION_STATUS_FIELDS,
    CURRENT_TIME_FIELD_KEY,
    CURRENT_TIME_FORMAT,
    DOMAIN,
    FIELDS,
    HARDWARE_FIELDS,
    ICON_LAN_SPEED,
    ICON_MAC_ADDRESS,
    LAN_1_SPEED_FIELD_KEY,
    LAN_2_SPEED_FIELD_KEY,
    LAN_3_SPEED_FIELD_KEY,
    LAN_4_SPEED_FIELD_KEY,
    LAN_FIELDS,
    LAN_MAC_ADDRESS_FIELD_KEY,
    LAN_PORT_SPEED_FIELD_KEYS,
    LAST_REBOOT_ICON,
    MEMORY_FIELD_KEYS,
    PROCESSOR_SPEED_FIELD_KEY,
    RETIRED_SENSOR_KEYS,
    SIGNAL_CONNECTIVITY_TEST,
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
    WIFI_SSID_FIELDS,
    ConnectionStatusField,
    GatewayField,
    HardwareField,
)
from .entity import XfinityEntity
from .util import build_list_selector, build_selector, entity_object_id

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
    coordinator_hardware = data["coordinator_hardware"]
    scraper_hardware = data["scraper_hardware"]
    device_info = data["device_info"]

    entities: list[SensorEntity] = [
        GatewayFieldSensor(hass, coordinator, scraper, field, device_info)
        for field in FIELDS
        if field.key not in RETIRED_SENSOR_KEYS
    ]
    entities.append(LastRebootSensor(hass, coordinator, scraper, device_info))
    entities.extend(
        CodewordSensor(hass, coordinator, scraper, field, device_info) for field in CODEWORD_FIELDS
    )
    entities.append(IpAddressSensor(hass, entry.data[CONF_HOST], device_info))

    for field in CONNECTION_STATUS_FIELDS:
        if field.key in RETIRED_SENSOR_KEYS:
            continue
        entity_cls = NumericGatewayFieldSensor if field.numeric else GatewayFieldSensor
        entities.append(entity_cls(hass, coordinator_cs, scraper_cs, field, device_info))

    entities.append(WifiClientCountSensor(hass, coordinator_cs, scraper_cs, device_info))

    entities.extend(
        (LanPortSpeedSensor if field.key in LAN_PORT_SPEED_FIELD_KEYS else GatewayFieldSensor)(
            hass, coordinator_lan, scraper_lan, field, device_info
        )
        for field in LAN_FIELDS
        if field.key not in RETIRED_SENSOR_KEYS
    )
    entities.extend(
        GatewayFieldSensor(hass, coordinator_wifi, scraper_wifi, field, device_info)
        for field in WIFI_MAC_FIELDS
    )
    entities.append(LanSpeedSensor(hass, coordinator_lan, scraper_lan, device_info))
    entities.append(
        MacAddressSensor(
            hass, coordinator_lan, scraper_lan, coordinator_wifi, scraper_wifi, device_info
        )
    )

    for field in HARDWARE_FIELDS:
        if field.key in MEMORY_FIELD_KEYS:
            entity_cls = MemoryFieldSensor
        elif field.key == PROCESSOR_SPEED_FIELD_KEY:
            entity_cls = ProcessorSpeedSensor
        else:
            entity_cls = GatewayFieldSensor
        entities.append(entity_cls(hass, coordinator_hardware, scraper_hardware, field, device_info))

    entities.extend(
        GatewayFieldSensor(hass, data["coordinator_wireless"], data["scraper_wireless"], field, device_info)
        for field in WIFI_SSID_FIELDS
    )
    entities.append(ConnectivityTestPacketLossSensor(hass, entry.entry_id, device_info))

    async_add_entities(entities)


class GatewayFieldSensor(XfinityEntity, SensorEntity):
    """A sensor reading a single field off a gateway status page.

    Works for GatewayField (network_setup.jst), ConnectionStatusField
    (connection_status.jst/lan.jst/wifi.jst) or HardwareField (hardware.jst) -
    all three just carry key/name/select.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator,
        scraper,
        field: GatewayField | ConnectionStatusField | HardwareField,
        device_info,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, scraper, field.name, None, False, None, None, {})

        self._attr_device_info = device_info
        self._attr_unique_id = f"xfinity_gateway_{field.key}"
        self._attr_translation_key = field.key
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, entity_object_id(self._attr_name), hass=hass
        )
        self._field_key = field.key
        self._attr_icon = STATIC_ICONS.get(field.key)
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


class MemoryFieldSensor(GatewayFieldSensor):
    """A GatewayFieldSensor whose value is a "<n> MB" memory size (DRAM/Flash usage).

    The gateway's "MB" is binary (MiB), so the native unit is MEBIBYTES.

    Uses _LEADING_INT_RE (defined below, alongside LanSpeedSensor) - safe to
    reference here since it's resolved at call time, not class-definition time.
    """

    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_native_unit_of_measurement = UnitOfInformation.MEBIBYTES
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _update_sensor(self) -> None:
        """Update state from the scraper data, parsed as an integer MB value."""
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

        match = _LEADING_INT_RE.search(str(raw_value) if raw_value is not None else "")
        if not match:
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Could not parse %s as a memory size in MB (raw value %r)",
                self.scraper.name,
                self._name,
                raw_value,
            )
            return

        self._attr_native_value = int(match.group())


class ProcessorSpeedSensor(GatewayFieldSensor):
    """A GatewayFieldSensor whose value is a "<n> MHz" processor speed."""

    _attr_device_class = SensorDeviceClass.FREQUENCY
    _attr_native_unit_of_measurement = UnitOfFrequency.MEGAHERTZ
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _update_sensor(self) -> None:
        """Update state from the scraper data, parsed as an integer MHz value."""
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

        match = _LEADING_INT_RE.search(str(raw_value) if raw_value is not None else "")
        if not match:
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Could not parse %s as a frequency in MHz (raw value %r)",
                self.scraper.name,
                self._name,
                raw_value,
            )
            return

        self._attr_native_value = int(match.group())


class LastRebootSensor(XfinityEntity, SensorEntity):
    """Derived timestamp sensor: the gateway's own reported current time minus its
    reported system uptime.

    Deliberately anchored to the gateway's own clock (its "Current Time" field)
    rather than Home Assistant's utcnow() - this mirrors the previously-validated
    manual Template Helper this integration replaces, and avoids drift if the
    gateway's clock and HA's clock disagree.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, coordinator, scraper, device_info) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, scraper, "Last Reboot", None, False, None, None, {})

        self._attr_device_info = device_info
        self._attr_icon = LAST_REBOOT_ICON
        self._attr_unique_id = "xfinity_gateway_last_reboot"
        self._attr_translation_key = "last_reboot"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, entity_object_id(self._attr_name), hass=hass
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


class WifiClientCountSensor(XfinityEntity, SensorEntity):
    """Derived sensor: sum of the three per-band Wi-Fi client counts.

    Re-scrapes all three band selectors itself each cycle, the same way
    LastRebootSensor recomputes from its own source fields rather than
    reading other entities' states (fragile/order-dependent).
    """

    _attr_device_class = None
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass: HomeAssistant, coordinator, scraper, device_info) -> None:
        """Initialize the sensor."""
        super().__init__(
            hass, coordinator, scraper, "Number of Wi-Fi Clients", None, False, None, None, {}
        )

        self._attr_device_info = device_info
        self._attr_icon = WIFI_CLIENT_COUNT_ICON
        self._attr_unique_id = "xfinity_gateway_wifi_client_count"
        self._attr_translation_key = "wifi_client_count"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, entity_object_id(self._attr_name), hass=hass
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


def _parse_mbps(raw: str | None) -> int | None:
    """"1000 Mbps" -> 1000; "Not Applicable" (port down) -> None."""
    match = _LEADING_INT_RE.search(raw or "")
    return int(match.group()) if match else None


class LanSpeedSensor(XfinityEntity, SensorEntity):
    """Derived sensor: the highest of the four LAN ports' speeds, in Mbit/s."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfDataRate.MEGABITS_PER_SECOND
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass: HomeAssistant, coordinator, scraper, device_info) -> None:
        """Initialize the sensor."""
        super().__init__(
            hass, coordinator, scraper, "LAN Speed", SensorDeviceClass.DATA_RATE, False, None, None, {}
        )

        self._attr_device_info = device_info
        self._attr_icon = ICON_LAN_SPEED
        self._attr_unique_id = "xfinity_gateway_lan_speed"
        self._attr_translation_key = "lan_speed"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, entity_object_id(self._attr_name), hass=hass
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

        speeds = [_parse_mbps(raw) for raw in raw_values]
        known = [speed for speed in speeds if speed is not None]
        self._attr_native_value = max(known) if known else None


class MacAddressSensor(XfinityEntity, SensorEntity):
    """Derived sensor: the gateway's "effective" MAC address.

    Priority order: LAN, then Wi-Fi 2.4/5/6 GHz - the first one that scrapes
    to a non-empty value wins. Reads from two different pages/scrapers (LAN
    and Wi-Fi), so it subscribes to the LAN coordinator for update timing
    (both run on the same configured scan_interval) but also holds a direct
    reference to the Wi-Fi scraper to read from it too.
    """

    _attr_device_class = None
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator_lan,
        scraper_lan,
        coordinator_wifi,
        scraper_wifi,
        device_info,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            hass, coordinator_lan, scraper_lan, "MAC Address", None, False, None, None, {}
        )

        self._attr_device_info = device_info
        self._attr_icon = ICON_MAC_ADDRESS
        self._attr_unique_id = "xfinity_gateway_mac_address"
        self._attr_translation_key = "mac_address"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, entity_object_id(self._attr_name), hass=hass
        )
        self._coordinator_wifi = coordinator_wifi
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
                self._scraper_wifi.scrape(
                    selector, self._name, context=self._coordinator_wifi.scrape_context
                )
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


class LanPortSpeedSensor(GatewayFieldSensor):
    """One LAN port's speed in Mbit/s ("Not Applicable" when the port is down -> unknown)."""

    _attr_native_unit_of_measurement = UnitOfDataRate.MEGABITS_PER_SECOND
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass: HomeAssistant, coordinator, scraper, field, device_info) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, scraper, field, device_info)
        self._attr_device_class = SensorDeviceClass.DATA_RATE

    def _update_sensor(self) -> None:
        """Update state from the scraper data."""
        super()._update_sensor()
        if not self._scrape_error:
            self._attr_native_value = _parse_mbps(self._attr_native_value)


class IpAddressSensor(SensorEntity):
    """The address Home Assistant reaches the gateway on (the configured host, resolved)."""

    _attr_has_entity_name = True
    _attr_name = "IP Address"
    _attr_translation_key = "ip_address"

    def __init__(self, hass: HomeAssistant, host: str, device_info) -> None:
        """Initialize the sensor."""
        self._host = host
        self._attr_device_info = device_info
        self._attr_unique_id = "xfinity_gateway_ip_address"
        self._attr_icon = STATIC_ICONS.get("ip_address")
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, entity_object_id(self._attr_name), hass=hass
        )

    async def async_added_to_hass(self) -> None:
        """Resolve right away instead of waiting for the first poll."""
        self.async_schedule_update_ha_state(True)

    async def async_update(self) -> None:
        """Resolve the configured host."""
        try:
            self._attr_native_value = await self.hass.async_add_executor_job(
                socket.gethostbyname, self._host
            )
        except OSError:
            self._attr_native_value = None


class CodewordSensor(GatewayFieldSensor):
    """A downstream codeword counter, summed over all channels."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, hass: HomeAssistant, coordinator, scraper, field, device_info) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, scraper, field, device_info)
        self._selector = build_list_selector(hass, field.name, field.select)

    def _update_sensor(self) -> None:
        """Update state from the scraper data."""
        super()._update_sensor()
        if self._scrape_error:
            return
        try:
            self._attr_native_value = sum(int(v) for v in str(self._attr_native_value).split(","))
        except ValueError:
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Could not parse %s (raw value %r)",
                self.scraper.name,
                self._name,
                self._attr_native_value,
            )
            self._attr_native_value = None


class ConnectivityTestPacketLossSensor(RestoreSensor):
    """Packet loss of the last Test Connectivity run (see button.py)."""

    _attr_has_entity_name = True
    _attr_name = "Connectivity Test Packet Loss"
    _attr_translation_key = "connectivity_test_packet_loss"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry_id: str, device_info) -> None:
        """Initialize the sensor."""
        self._entry_id = entry_id
        self._attr_device_info = device_info
        self._attr_unique_id = "xfinity_gateway_connectivity_test_packet_loss"
        self._attr_icon = STATIC_ICONS.get("connectivity_test_packet_loss")
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, entity_object_id(self._attr_name), hass=hass
        )

    async def async_added_to_hass(self) -> None:
        """Restore the last result and listen for new ones."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last.native_value
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_CONNECTIVITY_TEST.format(self._entry_id), self._handle_result
            )
        )

    @callback
    def _handle_result(self, result) -> None:
        self._attr_native_value = result.packet_loss
        self.async_write_ha_state()
