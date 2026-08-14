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
        "IP Address",
        ".module.forms .form-row:nth-of-type(4) span.value",
    ),
    GatewayField(
        "external_default_gateway",
        "External Default Gateway",
        ".module.forms .form-row:nth-of-type(5) span.value",
    ),
    GatewayField(
        "external_ipv6_address",
        "IPv6 Address",
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
)

CONNECTION_STATUS_FIELD_KEY = "connection_status"
CURRENT_TIME_FIELD_KEY = "current_time"
SYSTEM_UPTIME_FIELD_KEY = "system_uptime"

# Format the gateway reports its own "Current Time" field in, e.g. "2026-08-14 09:12:03".
CURRENT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
