"""Nanoleaf lights – both whole-fixture and per-panel entities."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_RGB_COLOR,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.util import color as color_util
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .digital_twin import DigitalTwin
from .coordinator import NanoleafPanelCoordinator

_LOGGER = logging.getLogger(__name__)

SUPPORT_RGB = 0

class PanelLight(CoordinatorEntity, LightEntity):
    """Individual Nanoleaf tile as a LightEntity."""

    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(
        self,
        coordinator: NanoleafPanelCoordinator,
        twin: DigitalTwin,
        panel_id: int,
        unique_prefix: str,
    ) -> None:
        super().__init__(coordinator)
        self._twin = twin
        self._pid = panel_id
        self._attr_unique_id = f"{unique_prefix}_{panel_id}"
        self._attr_name = f"Panel {panel_id}"

    @property
    def is_on(self) -> bool:  # noqa: D401
        return self._twin.colors[self._pid] != (0, 0, 0)

    @property
    def rgb_color(self):
        return self._twin.colors[self._pid]

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: D401
        rgb = kwargs.get(ATTR_RGB_COLOR)
        if rgb is None and (hs := kwargs.get(ATTR_HS_COLOR)):
            rgb = color_util.color_hs_to_RGB(*hs)
        if rgb is None:
            rgb = (255, 255, 255)
        await self._twin.set_color(self._pid, rgb)
        await self._twin.sync()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: D401
        await self._twin.set_color(self._pid, (0, 0, 0))
        await self._twin.sync()
        self.async_write_ha_state()

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    twin: DigitalTwin = data["twin"]
    coordinator: NanoleafPanelCoordinator = data["coordinator"]

    entities = [
        PanelLight(coordinator, twin, pid, entry.entry_id) for pid in twin.colors
    ]
    async_add_entities(entities)
