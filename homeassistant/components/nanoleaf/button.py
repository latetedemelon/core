"""Button platform for Nanoleaf integration."""
from __future__ import annotations

import logging

from aionanoleaf import Nanoleaf

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NanoleafPanelCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nanoleaf button based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    nanoleaf = data["device"]
    coordinator = data["coordinator"]

    async_add_entities([NanoleafIdentifyButton(coordinator, nanoleaf)])


class NanoleafIdentifyButton(CoordinatorEntity[NanoleafPanelCoordinator], ButtonEntity):
    """Defines a Nanoleaf identify button entity."""

    _attr_has_entity_name = True
    _attr_name = "Identify"
    _attr_device_class = ButtonDeviceClass.IDENTIFY

    def __init__(self, coordinator: NanoleafPanelCoordinator, nanoleaf: Nanoleaf) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._nanoleaf = nanoleaf
        self._attr_unique_id = f"{nanoleaf.serial_no}_identify"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Identify the device."""
        await self._nanoleaf.identify()
