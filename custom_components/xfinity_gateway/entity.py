"""Base entity for the Xfinity Gateway integration."""
from __future__ import annotations

from custom_components.multiscrape.entity import MultiscrapeEntity


class XfinityEntity(MultiscrapeEntity):
    """A MultiscrapeEntity that takes its state from the already-fetched page when added.

    MultiscrapeEntity only computes state on the next poll, so after a reload
    switches, selects and binary sensors were unknown for up to a scan interval.
    """

    async def async_added_to_hass(self) -> None:
        """Compute the state right away from the coordinator's last fetch."""
        await super().async_added_to_hass()
        if self.coordinator.last_update_success:
            self._handle_coordinator_update()
