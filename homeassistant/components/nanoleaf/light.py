"""Nanoleaf lights – both whole-fixture and per-panel entities."""
from __future__ import annotations

import logging
from typing import Any, Tuple

from homeassistant.components.light import (
    ATTR_RGB_COLOR,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.util import color as color_util
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.exceptions import HomeAssistantError, ConfigEntryNotReady

from .const import DOMAIN
from .digital_twin import DigitalTwin
from .coordinator import NanoleafPanelCoordinator

_LOGGER = logging.getLogger(__name__)

SUPPORT_RGB = 0

class PanelLight(CoordinatorEntity[NanoleafPanelCoordinator], LightEntity):
    """Individual Nanoleaf tile as a LightEntity."""

    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NanoleafPanelCoordinator,
        twin: DigitalTwin,
        panel_id: int,
        unique_prefix: str,
    ) -> None:
        """Initialize a Nanoleaf panel light."""
        super().__init__(coordinator)
        self._twin = twin
        self._pid = panel_id
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{unique_prefix}_{panel_id}"

    @property
    def _panel_color(self) -> Tuple[int, int, int] | None:
        """Return the color for this panel from coordinator data."""
        return self.coordinator.data.get(self._pid)

    @property
    def is_on(self) -> bool:
        """Return true if the panel light is on."""
        color = self._panel_color
        return color is not None and color != (0, 0, 0)

    @property
    def rgb_color(self) -> Tuple[int, int, int] | None:
        """Return the rgb color value."""
        return self._panel_color

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the panel light to turn on."""
        rgb = kwargs.get(ATTR_RGB_COLOR)
        if rgb is None and (hs := kwargs.get(ATTR_HS_COLOR)):
            rgb = color_util.color_hs_to_RGB(*hs)
        if rgb is None:
            # Default to white if no color specified,
            # or potentially use the last known color?
            # Using white for now.
            rgb = (255, 255, 255)

        await self._set_panel_color(rgb)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the panel light to turn off."""
        await self._set_panel_color((0, 0, 0))

    async def _set_panel_color(self, rgb: Tuple[int, int, int]) -> None:
        """Set the panel color, sync, and update coordinator."""
        await self._twin.set_color(self._pid, rgb)
        try:
            await self._twin.sync()
        except HomeAssistantError as err:
            _LOGGER.error("Failed to sync panel %s: %s", self._pid, err)
            raise
        
        if self.coordinator.data is None:
            self.coordinator.data = {}
        if self.coordinator.data:
            self.coordinator.data[self._pid] = rgb
            self.coordinator.async_set_updated_data(self.coordinator.data)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Nanoleaf panel lights."""
    data = hass.data[DOMAIN][entry.entry_id]
    twin: DigitalTwin = data["twin"]
    coordinator: NanoleafPanelCoordinator = data["coordinator"]

    if coordinator.data is None:
        _LOGGER.error("Coordinator data not available during setup")
        raise ConfigEntryNotReady("Coordinator data not available")
        
    entities = [
        PanelLight(coordinator, twin, pid, entry.entry_id)
        for pid in coordinator.data
        if pid != 0 # Filter out PSU
    ]
    async_add_entities(entities)
