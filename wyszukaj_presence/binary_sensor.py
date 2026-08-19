"""Presence entities for Wyszukaj Presence."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .manager import PresenceManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one presence entity for every configured device."""
    manager: PresenceManager = entry.runtime_data
    entities: dict[str, WyszukajPresenceBinarySensor] = {}

    def _sync_entities() -> None:
        new_entities: list[WyszukajPresenceBinarySensor] = []
        for device in manager.devices:
            mac = device["mac"]
            if mac not in entities:
                entity = WyszukajPresenceBinarySensor(manager, device["name"], mac)
                entities[mac] = entity
                new_entities.append(entity)

        if new_entities:
            async_add_entities(new_entities)

        for entity in entities.values():
            if entity.hass is not None:
                entity.async_write_ha_state()

    entry.async_on_unload(manager.async_add_listener(_sync_entities))
    _sync_entities()


class WyszukajPresenceBinarySensor(BinarySensorEntity):
    """A Home/Away entity backed by wynik.json."""

    _attr_device_class = BinarySensorDeviceClass.PRESENCE
    _attr_should_poll = False

    def __init__(self, manager: PresenceManager, name: str, mac: str) -> None:
        self._manager = manager
        self._device_name = name
        self._mac = mac
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{mac.replace(':', '').lower()}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=name,
        )

    @property
    def is_on(self) -> bool | None:
        """Return True at home, False away and None when unknown."""
        return self._manager.presence_for_name(self._device_name)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Expose the configured MAC for troubleshooting."""
        return {"mac_address": self._mac}
