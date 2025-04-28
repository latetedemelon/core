"""Async Digital Twin helper for per‑panel control (no streaming).
Adapted for Home Assistant from nanoleafapi's sync version.
"""
from __future__ import annotations

import logging
from typing import Dict, Tuple, Set

import aiohttp

from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

class DigitalTwin:
    """Maintain a local (id -> RGB) shadow of the panel layout."""

    def __init__(self, nl): 
        self._nl = nl
        self._panel_ids: Set[int] = set()
        self.colors: Dict[int, Tuple[int, int, int]] = {}
        # Initial population will happen in refresh_layout

    # ---------------------------------------------------------------------
    @classmethod
    async def create(cls, nl):
        await nl.get_info()
        instance = cls(nl)
        await instance.refresh_layout()
        return instance
    
    async def refresh_layout(self) -> bool:
        """Refresh the panel layout and update color dictionary.
        
        Returns True if the panel layout changed (panels added/removed).
        """
        await self._nl.get_info()
        # Extract panel IDs from the layout
        new_panel_ids = {p.id for p in self._nl.layout.panels if p.id}
        
        if new_panel_ids == self._panel_ids:
            return False  # No change
            
        # Update internal panel ID tracking
        self._panel_ids = new_panel_ids
        
        # Add new panels with black color
        for pid in new_panel_ids:
            if pid not in self.colors:
                self.colors[pid] = (0, 0, 0)
                
        # Remove panels that no longer exist
        self.colors = {pid: rgb for pid, rgb in self.colors.items() if pid in new_panel_ids}
        
        _LOGGER.debug("Nanoleaf panel layout changed, now %d panels", len(self._panel_ids))
        return True

    async def set_color(self, pid: int, rgb: Tuple[int, int, int]):
        if pid not in self.colors:
            raise ValueError(f"Unknown panel id {pid}")
        self.colors[pid] = rgb

    async def set_all(self, rgb: Tuple[int, int, int]):
        for pid in self.colors:
            self.colors[pid] = rgb

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _build_anim(ids: list[int], colours: Dict[int, Tuple[int, int, int]], transition: int) -> str:
        rec = []
        for pid in ids:
            r, g, b = colours[pid]
            rec.extend([pid, 1, r, g, b, 0, transition])
        return " ".join(map(str, [len(ids)] + rec))

    async def sync(self, transition_ms: int = 100):
        """Push current shadow to the controller as a static scene.
        
        The coordinator will handle checking for layout changes.
        """
        ids_ordered = sorted(self.colors)
        anim = self._build_anim(ids_ordered, self.colors, transition_ms // 10)
        payload = {
            "command": "display",
            "version": "1.0",
            "animType": "static",
            "animData": anim,
            "palette": [],
            "loop": False,
        }
        try:
            await self._nl.write_effect(payload)
        except aiohttp.ClientError as err:
            raise HomeAssistantError(f"Failed to write effect to Nanoleaf: {err}") from err
 