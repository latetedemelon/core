"""Constants for Nanoleaf integration."""
from datetime import timedelta

from homeassistant.const import CONF_TOKEN

DOMAIN = "nanoleaf"

NANOLEAF_EVENT = f"{DOMAIN}_event"

TOUCH_MODELS = {"NL29", "NL42", "NL52"}

# Minimum update interval for local network devices
SCAN_INTERVAL = 5

# Configuration options
CONF_EXPOSE_PANELS = "expose_panels"
DEFAULT_EXPOSE_PANELS = True

# Touch gesture mappings for events
TOUCH_GESTURE_TRIGGER_MAP = {
    2: "swipe_up",
    3: "swipe_down",
    4: "swipe_left",
    5: "swipe_right",
}
