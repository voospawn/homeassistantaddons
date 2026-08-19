"""Constants for the Wyszukaj Presence integration."""

from datetime import timedelta

DOMAIN = "wyszukaj_presence"

PANEL_URL = "wyszukaj-presence"
PANEL_TITLE = "Obecność"
PANEL_ICON = "mdi:account-plus"
PANEL_COMPONENT = "wyszukaj-presence-panel"
PANEL_STATIC_URL = "/wyszukaj_presence_static"
PANEL_MODULE_URL = f"{PANEL_STATIC_URL}/wyszukaj-presence.js?v=3.4.0"

DEVICES_FILENAME = "devices.json"
RESULT_FILENAME = "wynik.json"

RESULT_POLL_INTERVAL = timedelta(minutes=1)

PLATFORMS = ["binary_sensor"]
