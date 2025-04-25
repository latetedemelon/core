"""Nanoleaf Panel DataUpdateCoordinator.
Fetches on/off + RGB state for every panel so PanelLight entities stay in sync.
The coordinator stores a `panel_colors` dict {panel_id: (r,g,b)} updated every
SCAN_INTERVAL.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Dict, Tuple

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SCAN_INTERVAL
from .digital_twin import DigitalTwin

_LOGGER = logging.getLogger(__name__)

class NanoleafPanelCoordinator(DataUpdateCoordinator[Dict[int, Tuple[int, int, int]]]):
    """Coordinator that keeps current per‑panel colours cached."""

    def __init__(self, hass: HomeAssistant, twin: DigitalTwin):
        self._twin = twin
        super().__init__(
            hass,
            _LOGGER,
            name="Nanoleaf panel coordinator",
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> Dict[int, Tuple[int, int, int]]:  # noqa: D401
        """Return the most recently *sent* colours.
        Nanoleaf REST API cannot query per‑panel colour when an animation is
        running, so we rely on the DigitalTwin shadow.
        """
        return self._twin.colors.copy()
