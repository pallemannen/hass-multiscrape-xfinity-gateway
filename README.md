# hass-multiscrape-xfinity-gateway

A Home Assistant custom integration for monitoring Xfinity/Comcast Internet Gateway devices operating in bridge mode.

It depends on and reuses [multiscrape](https://github.com/danieldotnl/ha-multiscrape) (`danieldotnl/ha-multiscrape`) for the underlying HTTP session / form-login / CSS-scraping engine, instead of reimplementing that logic. `custom_components/xfinity_gateway/manifest.json` declares `"dependencies": ["multiscrape"]`, so Home Assistant refuses to start this integration - with a clear error - if multiscrape isn't installed.

## Installation

1. Install [multiscrape](https://github.com/danieldotnl/ha-multiscrape) via HACS (custom repository: `danieldotnl/ha-multiscrape`, category "Integration") if you don't already have it.
2. Add this repository to HACS as a custom repository (category "Integration"), then install "Xfinity Gateway".
3. Add your gateway credentials to `secrets.yaml`:

    ```yaml
    xfinity_username: admin
    xfinity_password: PutYourPasswordHere
    ```

4. Add this to `configuration.yaml` (or wherever you keep your package/device config):

    ```yaml
    xfinity_gateway:
      host: 10.0.0.1          # optional, defaults to 10.0.0.1
      username: !secret xfinity_username
      password: !secret xfinity_password
      scan_interval: 300      # optional, defaults to 300 seconds
    ```

5. Restart Home Assistant.

There is no config flow (it's YAML-only, matching how multiscrape itself is configured) and no UI setup step beyond that.

## What you get

All entities are created natively by the integration - no manual Template Helpers needed:

**Sensors**
- Connection Status, Current Time, System Uptime
- IP Address, External Default Gateway
- IPv6 Address, External IPv6 Default Gateway
- Primary/Secondary DNS, Primary/Secondary IPv6 DNS
- Serial Number
- **Last Reboot** (timestamp, derived from System Uptime)

**Binary sensor**
- **Connectivity** (device class `connectivity`, derived from Connection Status)

The two derived sensors used to require manually creating Template Helpers in Settings -> Devices and Services -> Helpers; that's no longer necessary, they ship built in.

## How it works

`custom_components/xfinity_gateway/__init__.py` builds one scraper config (resource URL, form-login details, CSS selectors) and hands it directly to multiscrape's own internal factory functions (`create_http_session`, `create_scraper`, `create_content_request_manager`, `create_multiscrape_coordinator` from `custom_components.multiscrape.*`) - the same functions multiscrape uses on itself. Sensor and binary sensor entities subclass multiscrape's `MultiscrapeEntity` base class directly, so availability handling and coordinator wiring come from multiscrape too.

multiscrape itself only parses its own `multiscrape:` YAML key once at HA startup and has no runtime API for another integration to hand it config afterwards - so rather than trying to inject config into multiscrape's own YAML processing, this integration builds and manages its own coordinator using multiscrape's reusable building blocks.

## Known limitation

The "System Uptime" -> "Last Reboot" parsing expects a format like `5 day(s) 3h:12m:45s`, matching this repo's previously-used manual Template Helper. If your gateway's firmware reports uptime in a different format, the Last Reboot sensor will log a warning and stay unavailable - open an issue with the raw value from your `sensor.xfinity_gateway_system_uptime` entity.
