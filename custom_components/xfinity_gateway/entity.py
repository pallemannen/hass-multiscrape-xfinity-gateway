"""Base entity for the Xfinity Gateway integration."""
from __future__ import annotations

from custom_components.multiscrape.entity import MultiscrapeEntity


class _NothingToSelect:
    """Stands in for _sensor_selector on entities that don't read a single field of their own page.

    multiscrape 9.2.0+ registers every entity's _sensor_selector with its scraper, which skips
    value-only selectors.
    """

    just_value = True


class XfinityEntity(MultiscrapeEntity):
    """A MultiscrapeEntity that takes its state from the already-fetched page when added.

    MultiscrapeEntity only computes state on the next poll, so after a reload
    switches, selects and binary sensors were unknown for up to a scan interval.
    """

    # multiscrape 9.2.0+ registers this with the scraper when the entity is added, and the scraper
    # then selects it off the event loop on every update. Entities that read one field of their own
    # page set it to that field's selector; the rest (derived from several fields or pages) keep the
    # stand-in and select on the loop, as with multiscrape 9.1.
    _sensor_selector = _NothingToSelect()

    async def async_added_to_hass(self) -> None:
        """Compute the state right away from the coordinator's last fetch."""
        await super().async_added_to_hass()
        if self.coordinator.last_update_success:
            self._handle_coordinator_update()

    def _restore_value(self, value: str) -> None:
        """Ignore the restored state (multiscrape 9.2.0+ requires this method).

        The state comes from the coordinator's last fetch as soon as the entity is added, and
        without one the entity is unavailable anyway. A restored state is only a string, which
        doesn't fit Last Reboot (a datetime) or the switches and selects.
        """
