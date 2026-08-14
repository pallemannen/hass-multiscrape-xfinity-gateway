# hass-multiscrape-xfinity-gateway

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=Integration&repository=hass-multiscrape-xfinity-gateway&owner=pallemannen)

A Home Assistant integration for monitoring an Xfinity/Comcast Internet Gateway: connection status, uptime, IP addresses, DNS servers, and more.

**Requires [multiscrape](https://github.com/danieldotnl/ha-multiscrape) to also be installed** - this integration uses it under the hood to talk to the gateway. Home Assistant will refuse to start this integration, with a clear error, if multiscrape isn't installed. 

## Gateway mode

This is for a gateway running in **bridge mode**. Support for **WiFi (router) mode** is on the to-do list and not available yet. But even in router mode, all the sensors in this integration should still work - it just won't give you any WiFi-related sensors.

## Installation

1. Install [multiscrape](https://github.com/danieldotnl/ha-multiscrape) via HACS (custom repository: `https://github.com/danieldotnl/ha-multiscrape`, category "Integration") if you don't already have it.
2. Add this repository to HACS as a custom repository (category "Integration"), then install "Xfinity Gateway".
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration**, search for "Xfinity Gateway", and fill in:
   - **Gateway IP address** (optional, defaults to `10.0.0.1`)
   - **Username** and **Password** for the gateway's admin login
   - **Scan interval** in seconds (optional, defaults to `300`)

   Your credentials are checked against the gateway during setup, so you'll see an error right away if the address is wrong or the login fails, rather than ending up with sensors that silently never update.

No YAML editing or manually edited config files needed - everything is set up through the UI.

## What you get

**Sensors**
- Connection Status, Current Time, System Uptime
- IP Address, External Default Gateway
- IPv6 Address, External IPv6 Default Gateway
- Primary/Secondary DNS, Primary/Secondary IPv6 DNS
- Serial Number
- **Last Reboot** (timestamp, calculated from System Uptime)

**Binary sensor**
- **Connectivity** (shows as a connectivity/online sensor, based on Connection Status)

All of these are created automatically when you set up the integration - nothing extra to configure.

## Known limitation

The Last Reboot sensor expects the gateway's uptime to be reported in a format like `5 day(s) 3h:12m:45s`. If your gateway reports it differently, that one sensor will log a warning and stay unavailable rather than show a wrong time - please open an issue with the raw value from the System Uptime sensor so the format can be added.
