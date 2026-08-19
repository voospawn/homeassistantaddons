"""WebSocket API for the Wyszukaj Presence panel."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .manager import PresenceManager


def _manager(hass: HomeAssistant) -> PresenceManager | None:
    data = hass.data.get(DOMAIN)
    return data if isinstance(data, PresenceManager) else None


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/get_devices"})
@websocket_api.async_response
async def websocket_get_devices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Return configured devices and their current status."""
    manager = _manager(hass)
    if manager is None:
        connection.send_error(msg["id"], "not_loaded", "Integration is not loaded")
        return

    connection.send_result(msg["id"], {"devices": manager.devices_for_frontend()})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/add_device",
        vol.Required("name"): str,
        vol.Required("mac"): str,
    }
)
@websocket_api.async_response
async def websocket_add_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Add and persist a device."""
    manager = _manager(hass)
    if manager is None:
        connection.send_error(msg["id"], "not_loaded", "Integration is not loaded")
        return

    try:
        devices = await manager.async_add_device(msg["name"], msg["mac"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_device", str(err))
        return
    except OSError as err:
        connection.send_error(msg["id"], "save_failed", f"Nie mo\u017cna zapisa\u0107 devices.json: {err}")
        return

    connection.send_result(msg["id"], {"devices": devices})


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register panel WebSocket commands once."""
    websocket_api.async_register_command(hass, websocket_get_devices)
    websocket_api.async_register_command(hass, websocket_add_device)
