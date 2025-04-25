"""Async Digital Twin helper for per‑panel control (no streaming).
Adapted for Home Assistant from nanoleafapi's sync version.
"""
from __future__ import annotations

from typing import Dict, Tuple

class DigitalTwin:  # pylint: disable=too-few-public-methods
    """Maintain a local (id -> RGB) shadow of the panel layout."""

    def __init__(self, nl):  # nl: aionanoleaf.Nanoleaf
        self._nl = nl
        self.colors: Dict[int, Tuple[int, int, int]] = {
            p.id: (0, 0, 0) for p in nl.layout.panels if p.id
        }

    # ---------------------------------------------------------------------
    @classmethod
    async def create(cls, nl):
        await nl.get_info()
        return cls(nl)

    async def set_color(self, pid: int, rgb: Tuple[int, int, int]):
        if pid not in self.colors:
            raise ValueError("Unknown panel id %s", pid)
        self.colors[pid] = rgb

    async def set_all(self, rgb: Tuple[int, int, int]):
        for pid in self.colors:
            self.colors[pid] = rgb

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _build_anim(ids, colours, transition: int) -> str:
        rec = []
        for pid in ids:
            r, g, b = colours[pid]
            rec.extend([pid, 1, r, g, b, 0, transition])
        return " ".join(map(str, [len(ids)] + rec))

    async def sync(self, transition_ms: int = 100):
        """Push current shadow to the controller as a static scene."""
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
        await self._nl.write_effect(payload)
