# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.4.0] - 2026-08-18

### Added

- `sensor.xfinity_gateway_mode`, reporting `Bridge` or `Router`, reusing the
  same Bridge Message detection text (`"in bridge mode"`) already used by
  `binary_sensor.xfinity_gateway_bridge_mode`. Icon switches between
  `mdi:bridge` and `mdi:router` depending on state. (#10)

### Fixed

- `binary_sensor.xfinity_gateway_connectivity` and
  `binary_sensor.xfinity_gateway_lan_connection` never actually reported
  `device_class: connectivity`. Both classes set `_attr_device_class` as a
  class attribute, but `MultiscrapeEntity.__init__` unconditionally does
  `self._attr_device_class = device_class` from its own constructor
  parameter - which both classes called with `None`. That instance
  assignment ran after the class body, silently overwriting the class
  attribute back to `None` on every setup, so the entities always reported
  `device_class: null` regardless of source, on every version since v1.3.1.
  Fixed by passing the device class through the constructor instead. (#11)

## [1.3.2] - 2026-08-15

### Fixed

- Bridge Message icon never rendering - `mdi:bridge-mode` isn't a real
  Material Design Icon, `mdi:bridge` is.

## [1.3.1] - 2026-08-15

### Fixed

- Client-count sensors (LAN, Wi-Fi 2.4/5/6 GHz, derived WiFi total) crashing
  with `'int' object has no attribute 'strip'` - the shared value_template's
  `parse_result=True` silently converts a bare number like `"0"` into a
  native int before it reaches our code.

### Changed

- Renamed "IP Address"/"IPv6 Address" to "External IP Address"/"External
  IPv6 Address" to avoid colliding with the new LAN IP Address sensor.
- Renamed "Vendor" to "Manufacturer" to match its entity_id.
- Wi-Fi 2.4/5/6 GHz Status sensors now show a dynamic wifi/wifi-off icon
  based on Active state.

## [1.3.0] - 2026-08-15

### Added

- Large feature addition - scrapes four gateway pages now instead of one,
  sharing a single authenticated session:
  - `network_setup.jst`: DHCP Client (IPv4/IPv6), Vendor, Model, Product
    Type, Software Version, Bridge Message
  - `connection_status.jst` (new): LAN IP/Netmask/DHCP Server
    Status/Client Count, per-band (2.4/5/6 GHz) Wi-Fi status and client
    counts, derived Number of WiFi Clients
  - `lan.jst` (new): per-port (1-4) LAN connection status and speed, LAN
    MAC Address, derived LAN Connection and LAN Speed
  - `wifi.jst` (new): per-band Wi-Fi MAC addresses, derived overall MAC
    Address (LAN > 2.4GHz > 5GHz > 6GHz priority)
  - New binary sensors: DHCP Client, DHCPv6 Client, DHCP Server, Bridge
    Mode (custom Enabled/Disabled wording), WiFi, LAN Connection

## [1.1.2] - 2026-08-15

### Changed

- Reverted the temporary debug logging from v1.1.1 - the underlying
  scraping failure was just a wrong stored password, now fixed via
  Reconfigure. No functional change beyond turning `log_response` back off.

## [1.1.0] - 2026-08-14

### Added

- Icons for all 14 entities, shipped with the integration (Connection
  Status and Connectivity change based on state).
- Reconfigure option (Settings -> Devices & Services -> Xfinity Gateway ->
  Reconfigure) to change host/username/password/scan interval without
  deleting and re-adding the integration.

### Fixed

- Config flow now correctly detects a failed login on gateways that return
  HTTP 200 for every page regardless of auth state, by checking for the
  login page's own header instead of relying on HTTP error codes.

## [1.0.2] - 2026-08-14

### Fixed

- Config entry setup crashing with `RuntimeError: This should only be used
  outside of config entries.` - the coordinator's shutdown was being
  registered manually (correct for multiscrape's own YAML-only use, wrong
  for our config-entry-based setup, where HA core already handles it
  automatically).

## [1.0.1] - 2026-08-14

### Added

- First release of the Xfinity Gateway custom integration.
- Real HA integration depending on multiscrape, reusing its HTTP session /
  form-auth / scraper / coordinator internals directly instead of
  reimplementing them.
- Config flow (host/username/password/scan interval), credentials
  validated live against the gateway during setup.
- Native Connectivity and Last Reboot sensors, replacing manual Template
  Helpers. Last Reboot is anchored on the gateway's own reported clock, not
  Home Assistant's.
- Swedish (sv) translation.

### Fixed

- Config flow failing with "Failed dependencies multiscrape" when
  multiscrape has no `multiscrape:` YAML config of its own - the
  integration only needs multiscrape installed, not loaded.
