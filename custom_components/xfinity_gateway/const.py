"""Constants for the Xfinity Gateway integration."""
from __future__ import annotations

from dataclasses import dataclass

DOMAIN = "xfinity_gateway"

CONF_HOST = "host"
DEFAULT_HOST = "10.0.0.1"
DEFAULT_SCAN_INTERVAL = 300

VALUE_TEMPLATE_STRIP = "{{ value.strip() }}"


@dataclass(frozen=True)
class GatewayField:
    """A single scraped field on the gateway's network_setup.jst status page."""

    key: str
    name: str
    select: str


# CSS selectors verified against the working multiscrape config previously
# maintained by hand in this user's devices.yaml.
FIELDS: tuple[GatewayField, ...] = (
    GatewayField(
        "connection_status",
        "Connection Status",
        ".module.forms .form-row:nth-of-type(1) span.value",
    ),
    GatewayField(
        "current_time",
        "Current Time",
        ".module.forms .form-row:nth-of-type(2) span.value",
    ),
    GatewayField(
        "system_uptime",
        "System Uptime",
        ".module.forms .form-row:nth-of-type(3) span.value",
    ),
    GatewayField(
        "external_ip_address",
        "External IP Address",
        ".module.forms .form-row:nth-of-type(4) span.value",
    ),
    GatewayField(
        "external_default_gateway",
        "External Default Gateway",
        ".module.forms .form-row:nth-of-type(5) span.value",
    ),
    GatewayField(
        "external_ipv6_address",
        "External IPv6 Address",
        ".module.forms .form-row:nth-of-type(6) span.value",
    ),
    GatewayField(
        "external_ipv6_default_gateway",
        "External IPv6 Default Gateway",
        ".module.forms .form-row:nth-of-type(7) span.value",
    ),
    GatewayField(
        "primary_dns",
        "Primary DNS",
        ".module.forms .form-row:nth-of-type(9) span.value",
    ),
    GatewayField(
        "secondary_dns",
        "Secondary DNS",
        ".module.forms .form-row:nth-of-type(10) span.value",
    ),
    GatewayField(
        "primary_ipv6_dns",
        "Primary IPv6 DNS",
        ".module.forms .form-row:nth-of-type(11) span.value",
    ),
    GatewayField(
        "secondary_ipv6_dns",
        "Secondary IPv6 DNS",
        ".module.forms .form-row:nth-of-type(12) span.value",
    ),
    GatewayField(
        "serial_number",
        "Serial Number",
        ".module.forms.dev_label .form-row:nth-of-type(3) span.value",
    ),
    GatewayField(
        "dhcp_client_ipv4",
        "DHCP Client (IPv4)",
        ".module.forms .form-row:nth-of-type(14) span.value",
    ),
    GatewayField(
        "dhcp_client_ipv6",
        "DHCP Client (IPv6)",
        ".module.forms .form-row:nth-of-type(15) span.value",
    ),
    # The "Device Information" block also just uses the plain "module forms"
    # class (reused by many blocks on this page, unlike Serial Number's
    # dev_label-marked block), so it can't be targeted by class alone. It's
    # verified (via a structural parse of a real captured page, since bs4
    # isn't installable in the dev environment) to be the 12th <div> at its
    # nesting level, so :nth-of-type(12) - not soupsieve extension syntax -
    # scopes to it unambiguously.
    GatewayField(
        "manufacturer",
        "Manufacturer",
        ".module.forms:nth-of-type(12) .form-row:nth-of-type(2) span.value",
    ),
    GatewayField(
        "model_number",
        "Model",
        ".module.forms:nth-of-type(12) .form-row:nth-of-type(4) span.value",
    ),
    GatewayField(
        "model",
        "Product Type",
        ".module.forms:nth-of-type(12) .form-row:nth-of-type(5) span.value",
    ),
    # "Download Version" on the real page - the closest thing to a firmware/
    # software version string; there's no field literally labeled that.
    GatewayField(
        "software_version",
        "Software Version",
        ".module.forms:nth-of-type(12) .form-row:nth-of-type(7) span.value",
    ),
    # Not a .form-row/span.value pair like the rest - a standalone paragraph.
    GatewayField(
        "bridge_message",
        "Bridge Message",
        "#bridmess",
    ),
)


@dataclass(frozen=True)
class ConnectionStatusField:
    """A single scraped field on the gateway's connection_status.jst page (LAN/Wi-Fi)."""

    key: str
    name: str
    select: str
    numeric: bool = False


# connection_status.jst reuses id="noclients" four times (LAN + all three Wi-Fi
# bands) and the same plain module/private-wifi classes across all three Wi-Fi
# band blocks - both invalid but real. The LAN one is disambiguated for free
# since BeautifulSoup's select_one() (like any CSS engine) resolves a bare
# #id selector to the first matching element in document order, and the LAN
# block happens to be first on the page. The Wi-Fi bands need :nth-of-type
# position scoping instead (verified the same way as Device Information
# above): the three .private-wifi blocks are siblings 1/2/3 under their own
# parent, and nothing else there shares that class.
CONNECTION_STATUS_FIELDS: tuple[ConnectionStatusField, ...] = (
    ConnectionStatusField(
        "lan_ip_address",
        "IP Address",
        "#ipaddloc + span.value",
    ),
    ConnectionStatusField(
        "lan_netmask",
        "Netmask",
        "#subnetloc + span.value",
    ),
    ConnectionStatusField(
        "lan_dhcp_server_status",
        "DHCP Server Status",
        "#dhcpserverloc + span.value",
    ),
    ConnectionStatusField(
        "lan_client_count",
        "Number of LAN Clients",
        "#noclients + span.value",
        numeric=True,
    ),
    ConnectionStatusField(
        "wifi_24ghz_status",
        "Wi-Fi 2.4 GHz Status",
        ".private-wifi:nth-of-type(1) .form-row:nth-of-type(1) span.value",
    ),
    ConnectionStatusField(
        "wifi_24ghz_client_count",
        "Number of WiFi 2.4 GHz Clients",
        ".private-wifi:nth-of-type(1) .form-row:nth-of-type(4) span.value",
        numeric=True,
    ),
    ConnectionStatusField(
        "wifi_5ghz_status",
        "Wi-Fi 5 GHz Status",
        ".private-wifi:nth-of-type(2) .form-row:nth-of-type(1) span.value",
    ),
    ConnectionStatusField(
        "wifi_5ghz_client_count",
        "Number of WiFi 5 GHz Clients",
        ".private-wifi:nth-of-type(2) .form-row:nth-of-type(4) span.value",
        numeric=True,
    ),
    ConnectionStatusField(
        "wifi_6ghz_status",
        "Wi-Fi 6 GHz Status",
        ".private-wifi:nth-of-type(3) .form-row:nth-of-type(1) span.value",
    ),
    ConnectionStatusField(
        "wifi_6ghz_client_count",
        "Number of WiFi 6 GHz Clients",
        ".private-wifi:nth-of-type(3) .form-row:nth-of-type(4) span.value",
        numeric=True,
    ),
)

# lan.jst: four identical <div class="module forms block"> port blocks, no
# unique IDs at all (will break if the gateway's firmware ever reorders
# them - accepted tradeoff, there's no more stable marker available).
# Verified via structural parse: siblings 2/3/4/5 at their nesting level.
LAN_FIELDS: tuple[ConnectionStatusField, ...] = (
    ConnectionStatusField(
        "lan_1_connection_status",
        "LAN 1 Connection Status",
        ".module.forms.block:nth-of-type(2) .form-row:nth-of-type(1) span.value",
    ),
    ConnectionStatusField(
        "lan_2_connection_status",
        "LAN 2 Connection Status",
        ".module.forms.block:nth-of-type(3) .form-row:nth-of-type(1) span.value",
    ),
    ConnectionStatusField(
        "lan_3_connection_status",
        "LAN 3 Connection Status",
        ".module.forms.block:nth-of-type(4) .form-row:nth-of-type(1) span.value",
    ),
    ConnectionStatusField(
        "lan_4_connection_status",
        "LAN 4 Connection Status",
        ".module.forms.block:nth-of-type(5) .form-row:nth-of-type(1) span.value",
    ),
    ConnectionStatusField(
        "lan_1_speed",
        "LAN 1 Speed",
        ".module.forms.block:nth-of-type(2) .form-row:nth-of-type(3) span.value",
    ),
    ConnectionStatusField(
        "lan_2_speed",
        "LAN 2 Speed",
        ".module.forms.block:nth-of-type(3) .form-row:nth-of-type(3) span.value",
    ),
    ConnectionStatusField(
        "lan_3_speed",
        "LAN 3 Speed",
        ".module.forms.block:nth-of-type(4) .form-row:nth-of-type(3) span.value",
    ),
    ConnectionStatusField(
        "lan_4_speed",
        "LAN 4 Speed",
        ".module.forms.block:nth-of-type(5) .form-row:nth-of-type(3) span.value",
    ),
    # Same MAC on all four ports on this gateway - just grab port 1's.
    ConnectionStatusField(
        "lan_mac_address",
        "LAN MAC Address",
        ".module.forms.block:nth-of-type(2) .form-row:nth-of-type(2) span.value",
    ),
)

# wifi.jst: three identical <div class="module forms block"> band blocks, same
# no-unique-ID caveat as LAN_FIELDS above. The MAC address row is present and
# populated even when a band's link status is "Inactive", so no conditional
# skip-logic is needed - always scrape directly. Verified siblings 2/3/4.
WIFI_MAC_FIELDS: tuple[ConnectionStatusField, ...] = (
    ConnectionStatusField(
        "wifi_24ghz_mac_address",
        "Wi-Fi 2.4 GHz MAC Address",
        ".module.forms.block:nth-of-type(2) .form-row:nth-of-type(2) span.value",
    ),
    ConnectionStatusField(
        "wifi_5ghz_mac_address",
        "Wi-Fi 5 GHz MAC Address",
        ".module.forms.block:nth-of-type(3) .form-row:nth-of-type(2) span.value",
    ),
    ConnectionStatusField(
        "wifi_6ghz_mac_address",
        "Wi-Fi 6 GHz MAC Address",
        ".module.forms.block:nth-of-type(4) .form-row:nth-of-type(2) span.value",
    ),
)

CONNECTION_STATUS_FIELD_KEY = "connection_status"
CURRENT_TIME_FIELD_KEY = "current_time"
SYSTEM_UPTIME_FIELD_KEY = "system_uptime"
DHCP_CLIENT_IPV4_FIELD_KEY = "dhcp_client_ipv4"
DHCP_CLIENT_IPV6_FIELD_KEY = "dhcp_client_ipv6"
BRIDGE_MESSAGE_FIELD_KEY = "bridge_message"

LAN_DHCP_SERVER_STATUS_FIELD_KEY = "lan_dhcp_server_status"
WIFI_24GHZ_STATUS_FIELD_KEY = "wifi_24ghz_status"
WIFI_5GHZ_STATUS_FIELD_KEY = "wifi_5ghz_status"
WIFI_6GHZ_STATUS_FIELD_KEY = "wifi_6ghz_status"
WIFI_STATUS_FIELD_KEYS = frozenset(
    {WIFI_24GHZ_STATUS_FIELD_KEY, WIFI_5GHZ_STATUS_FIELD_KEY, WIFI_6GHZ_STATUS_FIELD_KEY}
)
WIFI_24GHZ_CLIENT_COUNT_FIELD_KEY = "wifi_24ghz_client_count"
WIFI_5GHZ_CLIENT_COUNT_FIELD_KEY = "wifi_5ghz_client_count"
WIFI_6GHZ_CLIENT_COUNT_FIELD_KEY = "wifi_6ghz_client_count"

LAN_1_CONNECTION_STATUS_FIELD_KEY = "lan_1_connection_status"
LAN_2_CONNECTION_STATUS_FIELD_KEY = "lan_2_connection_status"
LAN_3_CONNECTION_STATUS_FIELD_KEY = "lan_3_connection_status"
LAN_4_CONNECTION_STATUS_FIELD_KEY = "lan_4_connection_status"
LAN_1_SPEED_FIELD_KEY = "lan_1_speed"
LAN_2_SPEED_FIELD_KEY = "lan_2_speed"
LAN_3_SPEED_FIELD_KEY = "lan_3_speed"
LAN_4_SPEED_FIELD_KEY = "lan_4_speed"
LAN_MAC_ADDRESS_FIELD_KEY = "lan_mac_address"
WIFI_24GHZ_MAC_ADDRESS_FIELD_KEY = "wifi_24ghz_mac_address"
WIFI_5GHZ_MAC_ADDRESS_FIELD_KEY = "wifi_5ghz_mac_address"
WIFI_6GHZ_MAC_ADDRESS_FIELD_KEY = "wifi_6ghz_mac_address"

# Format the gateway reports its own "Current Time" field in, e.g. "2026-08-14 09:12:03".
CURRENT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Connection Status and Connectivity get a state-dependent icon instead (see sensor.py /
# binary_sensor.py), so connection_status is deliberately absent from this map. Same for
# the Wi-Fi binary sensor, which switches between ICON_WIFI_ON/ICON_WIFI_OFF.
ICON_ACTIVE = "mdi:check-network-outline"
ICON_INACTIVE = "mdi:close-network-outline"
ICON_WIFI_ACTIVE = "mdi:wifi"
ICON_WIFI_INACTIVE = "mdi:wifi-off"
ICON_WIFI_ON = "mdi:wifi"
ICON_WIFI_OFF = "mdi:wifi-off"
LAST_REBOOT_ICON = "mdi:clock-time-four-outline"
ICON_DHCP = "mdi:database-export-outline"
ICON_BRIDGE = "mdi:bridge"
ICON_ROUTER = "mdi:router"
WIFI_CLIENT_COUNT_ICON = "mdi:wifi-settings"
ICON_LAN_SPEED = "mdi:speedometer"
ICON_MAC_ADDRESS = "mdi:barcode"

STATIC_ICONS: dict[str, str] = {
    "current_time": "mdi:clock-time-four-outline",
    "system_uptime": "mdi:clock-time-four-outline",
    "external_ip_address": "mdi:ip-network-outline",
    "external_default_gateway": "mdi:play-network-outline",
    "external_ipv6_address": "mdi:ip-network-outline",
    "external_ipv6_default_gateway": "mdi:play-network-outline",
    "primary_dns": "mdi:dns-outline",
    "secondary_dns": "mdi:dns-outline",
    "primary_ipv6_dns": "mdi:dns-outline",
    "secondary_ipv6_dns": "mdi:dns-outline",
    "serial_number": "mdi:numeric",
    "dhcp_client_ipv4": ICON_DHCP,
    "dhcp_client_ipv6": ICON_DHCP,
    "manufacturer": "mdi:factory",
    "model_number": "mdi:tag-outline",
    "model": "mdi:tag-outline",
    "software_version": "mdi:source-branch",
    "bridge_message": "mdi:bridge",
    "lan_ip_address": "mdi:ip-network-outline",
    "lan_netmask": "mdi:lan",
    "lan_dhcp_server_status": ICON_DHCP,
    "lan_client_count": "mdi:lan",
    "wifi_24ghz_client_count": "mdi:wifi-settings",
    "wifi_5ghz_client_count": "mdi:wifi-settings",
    "wifi_6ghz_client_count": "mdi:wifi-settings",
    "lan_1_connection_status": "mdi:lan",
    "lan_2_connection_status": "mdi:lan",
    "lan_3_connection_status": "mdi:lan",
    "lan_4_connection_status": "mdi:lan",
    "lan_1_speed": ICON_LAN_SPEED,
    "lan_2_speed": ICON_LAN_SPEED,
    "lan_3_speed": ICON_LAN_SPEED,
    "lan_4_speed": ICON_LAN_SPEED,
    "lan_mac_address": ICON_MAC_ADDRESS,
    "wifi_24ghz_mac_address": ICON_MAC_ADDRESS,
    "wifi_5ghz_mac_address": ICON_MAC_ADDRESS,
    "wifi_6ghz_mac_address": ICON_MAC_ADDRESS,
}
