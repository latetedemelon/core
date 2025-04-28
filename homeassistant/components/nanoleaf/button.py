"""Button platform for Nanoleaf integration."""
from __future__ import annotations

import logging

from aionanoleaf import Nanoleaf

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nanoleaf button based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    nanoleaf = data["device"]

    async_add_entities([NanoleafIdentifyButton(nanoleaf)])


class NanoleafIdentifyButton(ButtonEntity):
    """Defines a Nanoleaf identify button entity."""

    _attr_has_entity_name = True
    _attr_name = "Identify"
    _attr_device_class = ButtonDeviceClass.IDENTIFY

    def __init__(self, nanoleaf: Nanoleaf) -> None:
        """Initialize the button entity."""
        self._nanoleaf = nanoleaf
        self._attr_unique_id = f"{nanoleaf.serial_no}_identify"

    async def async_press(self) -> None:
        """Identify the device."""
        await self._nanoleaf.identify()
