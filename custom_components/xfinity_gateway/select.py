"""Wi-Fi Mode select for the Xfinity Gateway integration."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, WIFI_MODES, WIFI_RADIOS
from .wireless import WirelessEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Wi-Fi Mode select from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WifiModeSelect(
                hass, data["coordinator_wireless"], data["scraper_wireless"], data["client"],
                data["device_info"], "wifi_mode", "Wi-Fi Mode",
            )
        ]
    )


class WifiModeSelect(WirelessEntity, SelectEntity):
    """Which Wi-Fi radios are on."""

    _entity_id_format = "select.{}"
    _attr_options = list(WIFI_MODES)

    def _update_state(self) -> None:
        radios = self.radios()
        self._attr_current_option = next(
            (mode for mode, setting in WIFI_MODES.items() if setting == radios), None
        )

    async def async_select_option(self, option: str) -> None:
        """Set the radios for the chosen mode, changing only those that differ."""
        current = self.radios()
        await self.async_set_radios(
            {
                ssid_number: on
                for (_, _, _, ssid_number), on, now in zip(WIFI_RADIOS, WIFI_MODES[option], current)
                if on != now
            }
        )
