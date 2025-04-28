# Nanoleaf Integration

This integration provides support for [Nanoleaf](https://nanoleaf.me/) smart lighting panels, including Canvas, Shapes, Elements, and Lines.

## Features

- Control the entire light fixture as a single entity
- Individual panel control (optional) - each panel exposed as a separate light entity
- Gesture events for touch-enabled models
- Identification button
- Support for dynamic panel discovery - added panels will be automatically detected

## Configuration

This integration can be configured through the Home Assistant UI:

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Nanoleaf" and follow the setup instructions

### Options

After setup, you can configure the following options:

- **Expose panels**: Controls whether individual panels appear as separate light entities. When enabled, each panel will appear as a separate light entity with the name pattern `light.<device>_panel_<id>`.

## Gesture Events

Models with touch capability (Canvas, Shapes) support touch gestures that can trigger automations. 
The following gestures are supported:

- `swipe_up`
- `swipe_down`
- `swipe_left`
- `swipe_right`

## Technical Notes

- The integration uses a digital twin approach to track and control individual panel states
- Panel discovery is dynamic - if you add new panels while Home Assistant is running, they will be automatically detected and added
- Individual panels are grouped under the main device in the device tree
- Unique IDs are based on serial number to avoid collisions when multiple controllers are present

## Troubleshooting

If individual panels aren't showing up:
1. Check that "Expose panels" is enabled in the integration options
2. Verify the controller is operating in a compatible mode
3. Make sure the panels are properly connected and recognized by the Nanoleaf app
