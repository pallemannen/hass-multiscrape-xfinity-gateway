"""Gateway actions (Wi-Fi radios, restarts, connectivity test).

The gateway's own pages do these as AJAX posts to actionHandler/*.jst with a
CSRF token that is embedded in each page and changes on every page load. The
posts go through multiscrape's already logged-in session, so no second login.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from .const import (
    CONNECTIVITY_TEST_COUNT,
    CONNECTIVITY_TEST_DESTINATION,
    DIAGNOSTICS_PATH,
    RESTORE_REBOOT_PATH,
    WIRELESS_PATH,
)

_TOKEN_RE = re.compile(r'var token = "(\w+)"')


@dataclass(frozen=True)
class ConnectivityTestResult:
    """Result of the gateway's own Test Connectivity (a ping from the gateway)."""

    connected: bool | None
    packet_loss: float | None


class GatewayError(Exception):
    """A gateway action failed."""


class GatewayClient:
    """Posts actions to the gateway through the shared multiscrape session."""

    def __init__(self, session, host: str, username: str) -> None:
        """Initialize the client."""
        self._session = session
        self._base = f"http://{host}/"
        self.username = username

    async def _token(self, page: str) -> str:
        url = self._base + page
        for attempt in range(2):
            await self._session.ensure_authenticated(url)
            response = await self._session.async_request("action-page", url)
            if match := _TOKEN_RE.search(response.text):
                return match.group(1)
            # Logged out (the login page has no token): log in again once.
            if attempt == 0:
                self._session.invalidate_auth()
        raise GatewayError(f"No CSRF token on {page}; login failed?")

    async def async_post(self, page: str, action: str, data: dict[str, str]) -> str:
        """Post an action the way `page` itself does, returning the response text."""
        try:
            token = await self._token(page)
            response = await self._session.async_request(
                "action",
                f"{self._base}actionHandler/{action}",
                method="POST",
                request_data={**data, "csrfp_token": token},
            )
        except httpx.HTTPError as err:
            raise GatewayError(str(err)) from err
        return response.text

    async def async_post_json(self, page: str, action: str, data: dict[str, str]) -> Any:
        """Post an action that answers with JSON."""
        text = await self.async_post(page, action, data)
        try:
            return json.loads(text)
        except ValueError as err:
            raise GatewayError(f"Unexpected response from {action}: {text[:100]!r}") from err

    async def async_reset(self, button: tuple[str, str]) -> None:
        """Press one of the Reset/Restore page's buttons."""
        info = json.dumps([*button, self.username], separators=(",", ":"))
        await self.async_post(RESTORE_REBOOT_PATH, "ajaxSet_Reset_Restore.jst", {"resetInfo": info})

    async def async_set_radio(self, ssid_number: str, on: bool, wps_enabled: bool, wps_method: str) -> None:
        """Turn one Wi-Fi radio on or off, resending the current WPS settings like the page does."""
        config = {
            "radio_enable": "true" if on else "false",
            "wps_enabled": "true" if wps_enabled else "false",
            "wps_method": wps_method,
            "target": "save_enable",
            "sub_target": "radio_enable",
            "ssid_number": ssid_number,
        }
        info = json.dumps(config, separators=(",", ":"))
        await self.async_post(
            WIRELESS_PATH, "ajaxSet_wireless_network_configuration.jst", {"configInfo": info}
        )

    async def async_test_connectivity(self) -> ConnectivityTestResult:
        """Run Test Connectivity with the page's default destination and count."""
        result = await self.async_post_json(
            DIAGNOSTICS_PATH,
            "ajax_network_diagnostic_tools.jst",
            {
                "test_connectivity": "true",
                "destination_address": CONNECTIVITY_TEST_DESTINATION,
                "count1": str(CONNECTIVITY_TEST_COUNT),
            },
        )
        status = str(result.get("connectivity_internet", "")).split(":")[0].strip().lower()
        connected = {"active": True, "inactive": False}.get(status)
        try:
            received = int(result.get("success_received"))
        except (TypeError, ValueError):
            packet_loss = None
        else:
            packet_loss = round((CONNECTIVITY_TEST_COUNT - received) * 100 / CONNECTIVITY_TEST_COUNT, 1)
        return ConnectivityTestResult(connected, packet_loss)
