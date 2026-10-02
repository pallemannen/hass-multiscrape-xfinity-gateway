"""Binary sensors for the Xfinity Gateway integration."""
from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity


from .const import (
    BRIDGE_MESSAGE_FIELD_KEY,
    CONNECTION_STATUS_FIELD_KEY,
    CONNECTION_STATUS_FIELDS,
    DHCP_CLIENT_IPV4_FIELD_KEY,
    DHCP_CLIENT_IPV6_FIELD_KEY,
    DOMAIN,
    FIELDS,
    LAN_DHCP_SERVER_STATUS_FIELD_KEY,
    LAN_FIELDS,
    SIGNAL_CONNECTIVITY_TEST,
    WIFI_24GHZ_STATUS_FIELD_KEY,
    WIFI_5GHZ_STATUS_FIELD_KEY,
    WIFI_6GHZ_STATUS_FIELD_KEY,
)
from .entity import XfinityEntity
from .util import build_selector, entity_object_id

_LOGGER = logging.getLogger(__name__)
ENTITY_ID_FORMAT = "binary_sensor.{}"

_WIFI_BANDS = (
    ("wifi_24ghz", "Wi-Fi 2.4 GHz", WIFI_24GHZ_STATUS_FIELD_KEY),
    ("wifi_5ghz", "Wi-Fi 5 GHz", WIFI_5GHZ_STATUS_FIELD_KEY),
    ("wifi_6ghz", "Wi-Fi 6 GHz", WIFI_6GHZ_STATUS_FIELD_KEY),
)


def _field(fields, key):
    return next(f for f in fields if f.key == key)


class _Reader:
    """Reads one field from a scraper's latest page content."""

    def __init__(self, hass: HomeAssistant, coordinator, scraper, field) -> None:
        self._coordinator = coordinator
        self._scraper = scraper
        self._name = field.name
        self._selector = build_selector(hass, field.name, field.select)

    def value(self) -> str | None:
        value = self._scraper.scrape(
            self._selector, self._name, context=self._coordinator.scrape_context
        )
        return value.strip() if value else None


def _two_state(value: str | None, name: str, on: str, off: str) -> bool | None:
    """Map a gateway value to on/off; unexpected values become unknown (None)."""
    if not value:
        return None
    value = value.lower()
    if value == on:
        return True
    if value == off:
        return False
    _LOGGER.debug("Unexpected %s value %r", name, value)
    return None


def _any_on(states: list[bool | None]) -> bool | None:
    """On if any is on, off if all are off, otherwise unknown."""
    if any(state is True for state in states):
        return True
    if states and all(state is False for state in states):
        return False
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xfinity Gateway binary sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    main = (data["coordinator"], data["scraper"])
    cs = (data["coordinator_connection_status"], data["scraper_connection_status"])
    lan = (data["coordinator_lan"], data["scraper_lan"])
    device_info = data["device_info"]

    wan_reader = _Reader(hass, *main, _field(FIELDS, CONNECTION_STATUS_FIELD_KEY))
    port_readers = [
        _Reader(hass, *lan, _field(LAN_FIELDS, f"lan_{port}_connection_status"))
        for port in range(1, 5)
    ]
    band_readers = [
        _Reader(hass, *cs, _field(CONNECTION_STATUS_FIELDS, key)) for _, _, key in _WIFI_BANDS
    ]

    def wan() -> bool | None:
        # Anything other than "Active" means the WAN isn't up.
        value = wan_reader.value()
        return value.lower() == "active" if value is not None else None

    def port(reader: _Reader) -> bool | None:
        return _two_state(reader.value(), "LAN port", "active", "inactive")

    def band(reader: _Reader) -> bool | None:
        return _two_state(reader.value(), "Wi-Fi band", "active", "inactive")

    def lan_any() -> bool | None:
        return _any_on([port(r) for r in port_readers])

    def wifi_any() -> bool | None:
        return _any_on([band(r) for r in band_readers])

    def connectivity() -> bool | None:
        if not (up := wan()):
            return up
        lan_up, wifi_up = lan_any(), wifi_any()
        if lan_up or wifi_up:
            return True
        if lan_up is False and wifi_up is False:
            return False
        return None

    connectivity_class = BinarySensorDeviceClass.CONNECTIVITY
    entities: list[BinarySensorEntity] = [
        DerivedSensor(hass, *main, device_info, "connectivity", "Connectivity", connectivity,
                      connectivity_class, extra=(cs[0], lan[0])),
        DerivedSensor(hass, *main, device_info, "wan", "WAN", wan, connectivity_class),
        DerivedSensor(hass, *lan, device_info, "lan_connection", "LAN", lan_any, connectivity_class),
        DerivedSensor(hass, *cs, device_info, "wifi", "Wi-Fi", wifi_any),
    ]
    entities.extend(
        DerivedSensor(hass, *lan, device_info, f"lan_{n}", f"LAN {n}",
                      lambda r=reader: port(r), connectivity_class)
        for n, reader in enumerate(port_readers, start=1)
    )
    entities.extend(
        DerivedSensor(hass, *cs, device_info, key, name, lambda r=reader: band(r))
        for (key, name, _), reader in zip(_WIFI_BANDS, band_readers)
    )

    for key, name, coord, fields, field_key in (
        ("dhcp_client", "DHCP Client", main, FIELDS, DHCP_CLIENT_IPV4_FIELD_KEY),
        ("dhcpv6_client", "DHCPv6 Client", main, FIELDS, DHCP_CLIENT_IPV6_FIELD_KEY),
        ("dhcp_server", "DHCP Server", cs, CONNECTION_STATUS_FIELDS, LAN_DHCP_SERVER_STATUS_FIELD_KEY),
    ):
        reader = _Reader(hass, *coord, _field(fields, field_key))
        entities.append(
            DerivedSensor(hass, *coord, device_info, key, name,
                          lambda r=reader, n=name: _two_state(r.value(), n, "enabled", "disabled"),
                          translation_key="enabled_disabled")
        )

    bridge_reader = _Reader(hass, *main, _field(FIELDS, BRIDGE_MESSAGE_FIELD_KEY))

    def bridge_mode() -> bool | None:
        value = bridge_reader.value()
        return "in bridge mode" in value.lower() if value else None

    entities.append(
        DerivedSensor(hass, *main, device_info, "bridge_mode", "Bridge Mode", bridge_mode,
                      translation_key="bridge_mode")
    )
    entities.append(ConnectivityTestSensor(hass, entry.entry_id, device_info))
    async_add_entities(entities)


class DerivedSensor(XfinityEntity, BinarySensorEntity):
    """A binary sensor computed from the latest page data (icons from icons.json).

    device_class goes through MultiscrapeEntity's constructor: it overwrites a
    class-level _attr_device_class with its own argument.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator,
        scraper,
        device_info,
        key: str,
        name: str,
        compute: Callable[[], bool | None],
        device_class: BinarySensorDeviceClass | None = None,
        extra=(),
        translation_key: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, scraper, name, device_class, False, None, None, {})
        self._compute = compute
        self._extra_coordinators = extra
        self._attr_device_info = device_info
        self._attr_unique_id = f"xfinity_gateway_{key}"
        self._attr_translation_key = translation_key or key
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, entity_object_id(name), hass=hass
        )

    async def async_added_to_hass(self) -> None:
        """Also update when the other pages this sensor reads are refreshed."""
        await super().async_added_to_hass()
        for coordinator in self._extra_coordinators:
            self.async_on_remove(coordinator.async_add_listener(self._handle_coordinator_update))

    def _update_sensor(self) -> None:
        """Update state from the scraped data."""
        try:
            self._attr_is_on = self._compute()
        except Exception as exception:  # noqa: BLE001 - mirrors multiscrape's own broad on-error handling
            self.coordinator.request_reauth()
            self._scrape_error = True
            _LOGGER.warning(
                "%s # Unable to scrape %s: %s", self.scraper.name, self._name, exception
            )


class ConnectivityTestSensor(RestoreEntity, BinarySensorEntity):
    """Result of the last Test Connectivity run (see button.py)."""

    _attr_has_entity_name = True
    _attr_name = "Connectivity Test"
    _attr_translation_key = "connectivity_test"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry_id: str, device_info) -> None:
        """Initialize the sensor."""
        self._entry_id = entry_id
        self._attr_device_info = device_info
        self._attr_unique_id = "xfinity_gateway_connectivity_test"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, entity_object_id(self._attr_name), hass=hass
        )

    async def async_added_to_hass(self) -> None:
        """Restore the last result and listen for new ones."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state in ("on", "off"):
            self._attr_is_on = last.state == "on"
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_CONNECTIVITY_TEST.format(self._entry_id), self._handle_result
            )
        )

    @callback
    def _handle_result(self, result) -> None:
        self._attr_is_on = result.connected
        self.async_write_ha_state()
