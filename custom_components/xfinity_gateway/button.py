"""Buttons for the Xfinity Gateway integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import GatewayClient, GatewayError
from .const import DOMAIN, RESTART, RESTART_WIFI_MODULE, SIGNAL_CONNECTIVITY_TEST
from .util import entity_object_id

ENTITY_ID_FORMAT = "button.{}"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xfinity Gateway buttons from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    args = (hass, data["client"], data["device_info"])
    async_add_entities(
        [
            TestConnectivityButton(*args, entry.entry_id),
            RestartWifiModuleButton(*args),
            RestartButton(*args),
        ]
    )


class GatewayButton(ButtonEntity):
    """Runs one gateway action."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, client: GatewayClient, device_info, key: str) -> None:
        """Initialize the button."""
        self._client = client
        self._attr_unique_id = f"xfinity_gateway_{key}"
        self._attr_translation_key = key
        self._attr_device_info = device_info
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, entity_object_id(self._attr_name), hass=hass
        )


class TestConnectivityButton(GatewayButton):
    """Pings from the gateway; the result goes to Internet Connectivity Test and Packet Loss."""

    _attr_name = "Test Connectivity"

    def __init__(self, hass, client, device_info, entry_id: str) -> None:
        """Initialize the button."""
        super().__init__(hass, client, device_info, "test_connectivity")
        self._entry_id = entry_id

    async def async_press(self) -> None:
        """Run the test and publish the result."""
        try:
            result = await self._client.async_test_connectivity()
        except GatewayError as err:
            raise HomeAssistantError(f"{self.name} failed: {err}") from err
        async_dispatcher_send(self.hass, SIGNAL_CONNECTIVITY_TEST.format(self._entry_id), result)


class ResetButton(GatewayButton):
    """Presses one of the gateway's Reset/Restore buttons."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False
    _button: tuple[str, str]

    async def async_press(self) -> None:
        """Press the button."""
        try:
            await self._client.async_reset(self._button)
        except GatewayError as err:
            raise HomeAssistantError(f"{self.name} failed: {err}") from err


class RestartWifiModuleButton(ResetButton):
    """Restarts only the Wi-Fi module. Wi-Fi is down for about 90 seconds."""

    _attr_name = "Restart Wi-Fi Module"
    _button = RESTART_WIFI_MODULE

    def __init__(self, hass, client, device_info) -> None:
        """Initialize the button."""
        super().__init__(hass, client, device_info, "restart_wifi_module")


class RestartButton(ResetButton):
    """Restarts the gateway. Takes the internet connection down for a few minutes."""

    _attr_name = "Restart"
    _attr_device_class = ButtonDeviceClass.RESTART
    _button = RESTART

    def __init__(self, hass, client, device_info) -> None:
        """Initialize the button."""
        super().__init__(hass, client, device_info, "restart")
