"""Wi-Fi switches for the Xfinity Gateway integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, WIFI_RADIOS
from .wireless import WirelessEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Wi-Fi switches from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        WifiSwitch(
            hass, data["coordinator_wireless"], data["scraper_wireless"], data["client"],
            data["device_info"], key, name, variable, ssid_number,
        )
        for key, name, variable, ssid_number in WIFI_RADIOS
    )


class WifiSwitch(WirelessEntity, SwitchEntity):
    """Turns a Wi-Fi radio on or off."""

    _entity_id_format = "switch.{}"

    def __init__(self, hass, coordinator, scraper, client, device_info, key, name, variable, ssid_number) -> None:
        """Initialize the switch."""
        super().__init__(hass, coordinator, scraper, client, device_info, key, name)
        self._variable = variable
        self._ssid_number = ssid_number

    def _update_state(self) -> None:
        self._attr_is_on = self.radio(self._variable)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self.async_set_radios({self._ssid_number: True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self.async_set_radios({self._ssid_number: False})
