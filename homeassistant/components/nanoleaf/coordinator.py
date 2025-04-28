"""Nanoleaf Panel DataUpdateCoordinator.
Fetches on/off + RGB state for every panel so PanelLight entities stay in sync.
The coordinator stores a `panel_colors` dict {panel_id: (r,g,b)} updated every
SCAN_INTERVAL.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Tuple

from aionanoleaf import Nanoleaf

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_MODEL, ATTR_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .digital_twin import DigitalTwin

_LOGGER = logging.getLogger(__name__)

class NanoleafPanelCoordinator(DataUpdateCoordinator[Dict[int, Tuple[int, int, int]]]):
    """Coordinator that keeps current per‑panel colours cached."""

    def __init__(self, hass: HomeAssistant, twin: DigitalTwin, config_entry: ConfigEntry | None = None):
        """Initialize the coordinator with the provided twin."""
        self._twin = twin
        self._nanoleaf: Nanoleaf = twin._nl
        self.device_info = self._create_device_info()
        self.config_entry = config_entry
        
        super().__init__(
            hass,
            _LOGGER,
            name="Nanoleaf panel coordinator",
            update_interval=timedelta(seconds=15),  # Periodic updates to detect panel changes
        )
        
    def _create_device_info(self) -> dict[str, Any]:
        """Create device info for the Nanoleaf device."""
        return {
            "identifiers": {(DOMAIN, self._nanoleaf.serial_no)},
            "name": self._nanoleaf.name,
            "manufacturer": "Nanoleaf",
            "model": self._nanoleaf.model,
            "sw_version": self._nanoleaf.firmware_version,
        }

    async def _async_update_data(self) -> Dict[int, Tuple[int, int, int]]:  # noqa: D401
        """Return the most recently *sent* colours.
        Nanoleaf REST API cannot query per‑panel colour when an animation is
        running, so we rely on the DigitalTwin shadow.
        
        Also checks if the panel layout has changed and triggers discovery of new panels.
        """
        # If necessary, refresh layout to discover new panels
        panel_count_before = len(self._twin.colors)
        layout_changed = await self._twin.refresh_layout()
        
        # If new panels were discovered, trigger entity creation
        if layout_changed and len(self._twin.colors) > panel_count_before:
            _LOGGER.info("Panel layout changed: %d panels now available", len(self._twin.colors))
            # Use dispatcher to notify light platform about new panels
            async_dispatcher_send(
                self.hass,
                f"nanoleaf_new_panels_{self._nanoleaf.serial_no}",
                self._twin.colors.keys(),
            )
        
        return self._twin.colors.copy()
