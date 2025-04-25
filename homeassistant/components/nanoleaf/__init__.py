"""Home Assistant Nanoleaf integration – extended to expose individual panels."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import async_get_current_platform

from .const import DOMAIN, SCAN_INTERVAL
from .digital_twin import DigitalTwin
from .coordinator import NanoleafPanelCoordinator
from .light import NanoleafLight, PanelLight

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["light"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Nanoleaf integration from a config entry."""
    from aionanoleaf import Nanoleaf  # local import to keep requirements optional

    nl = Nanoleaf(entry.data["host"])
    await nl.authorize(token=entry.data["token"])

    twin = await DigitalTwin.create(nl)
    coordinator = NanoleafPanelCoordinator(hass, twin)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "device": nl,
        "twin": twin,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setup(entry, "light")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_forward_entry_unload(entry, "light")
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
