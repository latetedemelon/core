"""Event platform for Nanoleaf integration."""
from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from aionanoleaf import Nanoleaf

from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TOUCH_MODELS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Nanoleaf event entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    nanoleaf: Nanoleaf = data["device"]

    # Only add gesture events for devices that support them
    if nanoleaf.model in TOUCH_MODELS:
        async_add_entities([NanoleafGestureEventEntity(nanoleaf)])


class NanoleafGestureEventEntity(EventEntity):
    """Representation of a gesture event entity."""

    _attr_has_entity_name = True
    _attr_name = "Gesture"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = EventDeviceClass.GESTURE
    _attr_event_types = ["swipe_up", "swipe_down", "swipe_left", "swipe_right"]

    def __init__(self, nanoleaf: Nanoleaf) -> None:
        """Initialize the gesture event entity."""
        self._nanoleaf = nanoleaf
        self._attr_unique_id = f"{nanoleaf.serial_no}_gesture"
        # Device info is automatically set using the device registry info

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"nanoleaf_gesture_{self._nanoleaf.serial_no}",
                self._handle_event,
            )
        )

    @callback
    def _handle_event(self, event_type: str) -> None:
        """Handle the gesture event."""
        self._trigger_event(event_type)
        self.async_write_ha_state()
