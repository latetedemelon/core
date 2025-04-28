"""Nanoleaf lights – both whole-fixture and per-panel entities."""
from __future__ import annotations

import logging
from typing import Any, Tuple

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import color as color_util
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.exceptions import HomeAssistantError, ConfigEntryNotReady

from .const import CONF_EXPOSE_PANELS, DEFAULT_EXPOSE_PANELS, DOMAIN
from .digital_twin import DigitalTwin
from .coordinator import NanoleafPanelCoordinator

_LOGGER = logging.getLogger(__name__)

# Reserved effects names returned by the API
RESERVED_EFFECTS = ("*Solid*", "*Static*", "*Dynamic*")


class NanoleafLight(LightEntity):
    """Representation of the main Nanoleaf light fixture."""

    _attr_has_entity_name = True
    _attr_supported_color_modes = {ColorMode.COLOR_TEMP, ColorMode.HS}
    _attr_supported_features = LightEntityFeature.EFFECT | LightEntityFeature.TRANSITION
    _attr_name = None
    _attr_translation_key = "light"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, nanoleaf) -> None:
        """Initialize the Nanoleaf light."""
        self._nanoleaf = nanoleaf
        self._entry_id = entry.entry_id
        self._attr_unique_id = nanoleaf.serial_no
        self._attr_device_info = {
            "identifiers": {(DOMAIN, nanoleaf.serial_no)},
            "name": nanoleaf.name,
            "manufacturer": "Nanoleaf",
            "model": nanoleaf.model,
            "sw_version": nanoleaf.firmware_version,
        }
        self._attr_max_color_temp_kelvin = nanoleaf.color_temperature_max
        self._attr_min_color_temp_kelvin = nanoleaf.color_temperature_min

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return int(self._nanoleaf.brightness * 2.55)

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature value in Kelvin."""
        return self._nanoleaf.color_temperature

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        # The API returns the *Solid* effect if the Nanoleaf is in HS or CT mode.
        # The effects *Static* and *Dynamic* are not supported by Home Assistant.
        # These reserved effects are implicitly set and are not in the effect_list.
        return (
            None if self._nanoleaf.effect in RESERVED_EFFECTS else self._nanoleaf.effect
        )

    @property
    def effect_list(self) -> list[str]:
        """Return the list of supported effects."""
        return self._nanoleaf.effects_list

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._nanoleaf.is_on

    @property
    def hs_color(self) -> tuple[int, int]:
        """Return the color in HS."""
        return self._nanoleaf.hue, self._nanoleaf.saturation

    @property
    def color_mode(self) -> ColorMode | None:
        """Return the color mode of the light."""
        # According to API docs, color mode is "ct", "effect" or "hs"
        # https://forum.nanoleaf.me/docs/openapi#_4qgqrz96f44d
        if self._nanoleaf.color_mode == "ct":
            return ColorMode.COLOR_TEMP
        # Home Assistant does not have an "effect" color mode, just report hs
        return ColorMode.HS

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        hs_color = kwargs.get(ATTR_HS_COLOR)
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)
        effect = kwargs.get(ATTR_EFFECT)
        transition = kwargs.get(ATTR_TRANSITION)

        if effect:
            if effect not in self.effect_list:
                raise ValueError(
                    f"Attempting to apply effect not in the effect list: '{effect}'"
                )
            await self._nanoleaf.set_effect(effect)
        elif hs_color:
            hue, saturation = hs_color
            await self._nanoleaf.set_hue(int(hue))
            await self._nanoleaf.set_saturation(int(saturation))
        elif color_temp_kelvin:
            await self._nanoleaf.set_color_temperature(color_temp_kelvin)
        if transition:
            if brightness:  # tune to the required brightness in n seconds
                await self._nanoleaf.set_brightness(
                    int(brightness / 2.55), transition=int(kwargs[ATTR_TRANSITION])
                )
            else:  # If brightness is not specified, assume full brightness
                await self._nanoleaf.set_brightness(100, transition=int(transition))
        else:  # If no transition is occurring, turn on the light
            await self._nanoleaf.turn_on()
            if brightness:
                await self._nanoleaf.set_brightness(int(brightness / 2.55))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        transition: float | None = kwargs.get(ATTR_TRANSITION)
        await self._nanoleaf.turn_off(None if transition is None else int(transition))


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
        self._nanoleaf = coordinator.hass.data[DOMAIN][unique_prefix]["device"]
        
        # Set device info with via_device to group panels under main device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{self._nanoleaf.serial_no}_panel_{panel_id}")},
            "name": f"Nanoleaf Panel {panel_id}",
            "manufacturer": "Nanoleaf",
            "model": f"{self._nanoleaf.model} Panel",
            "via_device": (DOMAIN, self._nanoleaf.serial_no),
        }
        self._attr_unique_id = f"{self._nanoleaf.serial_no}_{panel_id}"
        self._attr_name = f"Panel {panel_id}"

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
        except Exception as err:
            _LOGGER.error("Failed to sync panel %s: %s", self._pid, err)
            raise HomeAssistantError(f"Failed to sync panel {self._pid}: {err}") from err

        # Update coordinator data
        if self.coordinator.data is None:
            self.coordinator.data = {}
        self.coordinator.data[self._pid] = rgb
        self.coordinator.async_set_updated_data(self.coordinator.data)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Nanoleaf panel lights."""
    data = hass.data[DOMAIN][entry.entry_id]
    twin: DigitalTwin = data["twin"]
    coordinator: NanoleafPanelCoordinator = data["coordinator"]
    nanoleaf = data["device"]
    expose_panels = data.get("expose_panels", DEFAULT_EXPOSE_PANELS)

    # Ensure coordinator had a chance to refresh data
    await coordinator.async_config_entry_first_refresh()
    
    if coordinator.data is None:
        _LOGGER.error("Coordinator data not available during setup")
        raise ConfigEntryNotReady("Coordinator data not available")
    
    # Create entities list starting with the main light
    entities = [NanoleafLight(hass, entry, nanoleaf)]
    
    # Track previously registered panel IDs to detect new panels
    registered_panel_ids = set()
    
    # Add individual panel lights if enabled in options
    if expose_panels:
        _LOGGER.debug("Setting up %d individual panel lights", len(coordinator.data))
        panel_entities = [
            PanelLight(coordinator, twin, pid, entry.entry_id)
            for pid in coordinator.data
            if pid != 0  # Filter out PSU
        ]
        # Record registered panel IDs
        registered_panel_ids.update(pid for pid in coordinator.data if pid != 0)
        entities.extend(panel_entities)
        
        # Register listener for new panels discovered by coordinator
        @callback
        def async_add_new_panels(panel_ids):
            """Add new panel entities when they are discovered."""
            new_panels = []
            
            # Find panel IDs that haven't been registered yet
            for pid in panel_ids:
                if pid != 0 and pid not in registered_panel_ids:  # Filter out PSU
                    new_panels.append(PanelLight(coordinator, twin, pid, entry.entry_id))
                    registered_panel_ids.add(pid)
                    
            if new_panels:
                _LOGGER.debug("Adding %d new panel lights", len(new_panels))
                async_add_entities(new_panels)
                
        # Listen for new panels signal
        entry.async_on_unload(
            async_dispatcher_connect(
                hass,
                f"nanoleaf_new_panels_{nanoleaf.serial_no}",
                async_add_new_panels
            )
        )
    
    # Add all entities
    async_add_entities(entities)
