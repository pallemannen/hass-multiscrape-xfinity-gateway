# hass-multiscrape-xfinity-gateway

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=Integration&repository=hass-multiscrape-xfinity-gateway&owner=pallemannen)

A Home Assistant integration for monitoring an Xfinity/Comcast Internet Gateway: connection status, uptime, IP addresses, DNS servers, and more.

**Requires [multiscrape](https://github.com/danieldotnl/ha-multiscrape) to also be installed** - this integration uses it under the hood to talk to the gateway. Home Assistant will refuse to start this integration, with a clear error, if multiscrape isn't installed. 

## Gateway mode

This was developed with a gateway running in **bridge mode**. Support for **WiFi (router) mode** has been added as well, but without a WiFi-enabled gateway to test things on, so please submitt an issue if something is not working.

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
- Connection status, current time, system uptime, last reboot
- MAC addresses, IP and IPv6 addresses, external default gateways, DNS servers, DHCP status
- LAN connections, WiFi information and number of clients
- Manufacturer, model, version, serial number

**Binary sensor**
- Connectivity, bridge mode, LAN connections, WiFi bands enabled

All of these are created automatically when you set up the integration - nothing extra to configure.

## HACS

More info about HACS can be found at https://www.hacs.xyz/

## License

MIT - see [LICENSE](LICENSE).
