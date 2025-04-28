"""Home Assistant Nanoleaf integration – extended to expose individual panels."""
from __future__ import annotations

import asyncio
from contextlib import suppress
import logging

from aionanoleaf import EffectsEvent, Nanoleaf, StateEvent, TouchEvent

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from .const import (
    CONF_EXPOSE_PANELS,
    DEFAULT_EXPOSE_PANELS,
    DOMAIN,
    NANOLEAF_EVENT,
    TOUCH_GESTURE_TRIGGER_MAP,
    TOUCH_MODELS,
)
from .digital_twin import DigitalTwin
from .coordinator import NanoleafPanelCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["light", "event", "button"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nanoleaf from a config entry."""
    session = async_get_clientsession(hass)
    nl = Nanoleaf(session, entry.data["host"])
    await nl.authorize(token=entry.data["token"])

    twin = await DigitalTwin.create(nl)
    coordinator = NanoleafPanelCoordinator(hass, twin, entry)
    await coordinator.async_config_entry_first_refresh()
    
    # Set up event listeners for state updates
    async def light_event_callback(event: StateEvent | EffectsEvent) -> None:
        """Receive state and effect event."""
        # Force refresh of the coordinator data
        coordinator.async_set_updated_data(coordinator.data)
    
    # Set up touch gesture events if supported
    if supports_touch := nl.model in TOUCH_MODELS:
        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, nl.serial_no)},
        )

        async def touch_event_callback(event: TouchEvent) -> None:
            """Receive touch event."""
            gesture_type = TOUCH_GESTURE_TRIGGER_MAP.get(event.gesture_id)
            if gesture_type is None:
                _LOGGER.warning("Received unknown touch gesture ID %s", event.gesture_id)
                return
            _LOGGER.debug("Received touch gesture %s", gesture_type)
            hass.bus.async_fire(
                NANOLEAF_EVENT,
                {CONF_DEVICE_ID: device_entry.id, CONF_TYPE: gesture_type},
            )
            async_dispatcher_send(
                hass, f"nanoleaf_gesture_{nl.serial_no}", gesture_type
            )

    # Create and start event listener task
    event_listener = asyncio.create_task(
        nl.listen_events(
            state_callback=light_event_callback,
            effects_callback=light_event_callback,
            touch_callback=touch_event_callback if supports_touch else None,
        )
    )

    # Function to cancel listener on unload
    async def _cancel_listener() -> None:
        """Cancel the event listener task."""
        event_listener.cancel()
        with suppress(asyncio.CancelledError):
            await event_listener

    entry.async_on_unload(_cancel_listener)
    
    # Register the device in the registry to get a consistent device ID
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, nl.serial_no)}
    ) or device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, nl.serial_no)},
        name=nl.name,
        manufacturer="Nanoleaf",
        model=nl.model,
        sw_version=nl.firmware_version,
    )
    
    # Create device info to share with entities
    device_info = {
        "identifiers": {(DOMAIN, nl.serial_no)},
        "name": nl.name,
        "manufacturer": "Nanoleaf",
        "model": nl.model,
        "sw_version": nl.firmware_version,
    }
    
    # Store data for use by platforms
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "device": nl,
        "twin": twin,
        "coordinator": coordinator,
        "device_id": device_entry.id,
        "device_info": device_info,
        "expose_panels": entry.options.get(CONF_EXPOSE_PANELS, DEFAULT_EXPOSE_PANELS),
    }
    
    # Also store key data by serial number for panel discovery
    hass.data.setdefault(DOMAIN, {})[nl.serial_no] = hass.data[DOMAIN][entry.entry_id]
    
    # Also store key data by serial number for panel discovery
    hass.data.setdefault(DOMAIN, {})[nl.serial_no] = hass.data[DOMAIN][entry.entry_id]

    # Determine which platforms to set up
    platforms_to_setup = ["button", "event"]  # Always set up these platforms
    
    # Only set up light platform if needed
    platforms_to_setup.append("light")
    
    # Set up all platforms
    for platform in platforms_to_setup:
        await hass.config_entries.async_forward_entry_setup(entry, platform)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
