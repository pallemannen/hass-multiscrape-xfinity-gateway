# hass-multiscrape-xfinity-gateway

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=Integration&repository=hass-multiscrape-xfinity-gateway&owner=pallemannen)

A Home Assistant integration for monitoring an Xfinity/Comcast Internet Gateway: connection status, uptime, IP addresses, DNS servers, and more.

**Requires [multiscrape](https://github.com/danieldotnl/ha-multiscrape) to also be installed** - this integration uses it under the hood to talk to the gateway. Home Assistant will refuse to start this integration, with a clear error, if multiscrape isn't installed. 

## Gateway mode

This was developed with a gateway running in **bridge mode**. Support for **Wi-Fi (router) mode** has been added as well, but without a Wi-Fi-enabled gateway to test things on, so please submitt an issue if something is not working.

## Installation

1. Install [multiscrape](https://github.com/danieldotnl/ha-multiscrape) via HACS (custom repository: `https://github.com/danieldotnl/ha-multiscrape`, category "Integration") if you don't already have it.
2. Add this repository to HACS as a custom repository (category "Integration"), then install "Xfinity Gateway".
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration**, search for "Xfinity Gateway", and fill in:
   - **Gateway IP address** (defaults to `10.0.0.1` - change it if yours is different)
   - **Device name** (defaults to `Xfinity Gateway` - change it if you want something else)
   - **Username** and **Password** for the gateway's admin login
   - **Scan interval** in seconds (defaults to `300` - change it if you want a different polling rate)

   Your credentials are checked against the gateway during setup, so you'll see an error right away if the address is wrong or the login fails, rather than ending up with sensors that silently never update.

No YAML editing or manually edited config files needed - everything is set up through the UI.

## What you get

**Sensors**
- Current time, system uptime, last reboot
- MAC address, IP address, LAN IP address and netmask, external IPv4/IPv6 addresses and default gateways, DNS servers
- LAN speed per port, Wi-Fi MAC addresses, number of LAN and Wi-Fi clients
- Manufacturer, model, product type, software/hardware version, serial number, processor speed, memory
- Wi-Fi 2.4/5/6 GHz SSID
- Unerrored, Correctable and Uncorrectable Codewords (summed over the downstream channels)
- Connectivity Test Packet Loss

**Binary sensors**
- Connectivity: WAN up and (any LAN port connected or any Wi-Fi band active)
- WAN, LAN (any port), LAN 1-4, Wi-Fi (any band), Wi-Fi 2.4/5/6 GHz
- DHCP Client, DHCPv6 Client, DHCP Server, Bridge Mode
- Connectivity Test

**Controls**
- Wi-Fi 2.4/5/6 GHz switches, and a Wi-Fi Mode select for which radios are on
- Test Connectivity: the gateway pings `www.comcast.net` 4 times; the result goes to Connectivity Test and Connectivity Test Packet Loss
- Restart Wi-Fi Module and Restart (disabled by default)

In bridge mode the gateway's own Wi-Fi is off, so the Wi-Fi switches and Wi-Fi Mode are unavailable then.

All of these are created automatically when you set up the integration - nothing extra to configure. Every entity is grouped under a single device (manufacturer/model/serial/version read from the gateway itself).

## HACS

More info about HACS can be found at https://www.hacs.xyz/

## License

MIT - see [LICENSE](LICENSE).
