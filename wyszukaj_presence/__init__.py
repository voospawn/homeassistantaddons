"""Wyszukaj Presence custom integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    PANEL_COMPONENT,
    PANEL_ICON,
    PANEL_MODULE_URL,
    PANEL_STATIC_URL,
    PANEL_TITLE,
    PANEL_URL,
    PLATFORMS,
    RESULT_POLL_INTERVAL,
)
from .manager import PresenceManager
from .websocket import async_register_websocket_commands


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up integration-level resources."""
    frontend_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_STATIC_URL, str(frontend_dir), False)]
    )
    async_register_websocket_commands(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration entry."""
    manager = PresenceManager(hass)
    await manager.async_initialize()
    hass.data[DOMAIN] = manager
    entry.runtime_data = manager

    await async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=PANEL_MODULE_URL,
        require_admin=False,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    remove_interval = async_track_time_interval(
        hass, manager.async_refresh_result, RESULT_POLL_INTERVAL
    )
    entry.async_on_unload(remove_interval)

    # wynik.json was already read during initialization; refresh again every minute.
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the integration entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    manager = hass.data.pop(DOMAIN, None)
    if isinstance(manager, PresenceManager):
        await manager.async_stop()

    frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
    return True
