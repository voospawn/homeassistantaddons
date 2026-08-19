"""Persistent device storage and wynik.json reader."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import json
import logging
import os
from pathlib import Path
import re
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    DEVICES_FILENAME,
    DOMAIN,
    RESULT_FILENAME,
)

_LOGGER = logging.getLogger(__name__)
_MAC_RE = re.compile(r"^[0-9A-Fa-f]{12}$")


class PresenceManager:
    """Manage configured devices and presence results."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.base_dir = Path(hass.config.path("custom_components", DOMAIN))
        self.devices_path = self.base_dir / DEVICES_FILENAME
        self.result_path = self.base_dir / RESULT_FILENAME

        self._devices: list[dict[str, str]] = []
        self._presence_by_name: dict[str, bool | None] = {}
        self._result_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._listeners: set[Callable[[], None]] = set()

    @property
    def devices(self) -> tuple[dict[str, str], ...]:
        """Return a stable snapshot of configured devices."""
        return tuple(dict(device) for device in self._devices)

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to device/status changes."""
        self._listeners.add(listener)

        def _remove() -> None:
            self._listeners.discard(listener)

        return _remove

    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            try:
                listener()
            except Exception:
                _LOGGER.exception("Presence listener failed")

    async def async_initialize(self) -> None:
        """Load persistent devices and the last valid result."""
        await self._async_load_devices()
        await self._async_load_result(log_problem=False)

    async def _async_load_devices(self) -> None:
        """Load devices.json, creating an empty file if necessary."""
        try:
            exists = await self.hass.async_add_executor_job(self.devices_path.exists)
            if not exists:
                self._devices = []
                self._presence_by_name = {}
                try:
                    await self._async_save_devices()
                except OSError as err:
                    _LOGGER.error("Cannot create %s: %s", self.devices_path, err)
                return

            raw = await self.hass.async_add_executor_job(
                self.devices_path.read_text, "utf-8"
            )
            if not raw.strip():
                _LOGGER.warning("%s is empty; using an empty device list", DEVICES_FILENAME)
                self._devices = []
                self._presence_by_name = {}
                return

            data = json.loads(raw)
            if not isinstance(data, list):
                raise ValueError("top-level JSON value must be a list")

            devices: list[dict[str, str]] = []
            normalization_changed = False
            for item in data:
                if not isinstance(item, dict):
                    raise ValueError("each device must be an object")
                name = item.get("name")
                mac = item.get("mac")
                if not isinstance(name, str) or not name.strip():
                    raise ValueError("each device needs a non-empty name")
                if not isinstance(mac, str) or not mac.strip():
                    raise ValueError("each device needs a non-empty mac")
                normalized_mac = self._normalize_mac(mac)
                if mac.strip() != normalized_mac:
                    normalization_changed = True
                devices.append({"name": name.strip(), "mac": normalized_mac})

            self._devices = devices
            self._presence_by_name = {device["name"]: None for device in devices}

            # Keep devices.json canonical: lower-case MAC with colon separators.
            if normalization_changed:
                try:
                    await self._async_save_devices()
                except OSError as err:
                    _LOGGER.warning("Cannot normalize %s: %s", self.devices_path, err)
        except (OSError, json.JSONDecodeError, ValueError) as err:
            _LOGGER.error("Cannot load %s: %s", self.devices_path, err)
            self._devices = []
            self._presence_by_name = {}

    async def _async_save_devices(self) -> None:
        """Atomically persist devices.json."""
        payload = json.dumps(self._devices, ensure_ascii=False, indent=2) + "\n"
        tmp_path = self.devices_path.with_name(f"{DEVICES_FILENAME}.tmp")

        def _write() -> None:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            tmp_path.write_text(payload, encoding="utf-8")
            os.replace(tmp_path, self.devices_path)

        await self.hass.async_add_executor_job(_write)

    @staticmethod
    def _normalize_mac(mac: str) -> str:
        compact = mac.strip().replace(":", "").replace("-", "")
        if not _MAC_RE.fullmatch(compact):
            raise ValueError("Niepoprawny adres MAC")
        compact = compact.lower()
        return ":".join(compact[index : index + 2] for index in range(0, 12, 2))

    async def async_add_device(self, name: str, mac: str) -> list[dict[str, Any]]:
        """Add a device and persist the complete list."""
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Nazwa urządzenia nie może być pusta")

        clean_mac = self._normalize_mac(mac)

        async with self._write_lock:
            if any(device["name"] == clean_name for device in self._devices):
                raise ValueError("Urządzenie o tej nazwie już istnieje")
            if any(device["mac"].lower() == clean_mac for device in self._devices):
                raise ValueError("Urządzenie o tym adresie MAC już istnieje")

            self._devices.append({"name": clean_name, "mac": clean_mac})
            self._presence_by_name[clean_name] = None
            try:
                await self._async_save_devices()
            except OSError:
                self._devices.pop()
                self._presence_by_name.pop(clean_name, None)
                raise

        self._notify_listeners()
        # Refresh from the existing wynik.json after adding a device.
        await self.async_refresh_result()
        return self.devices_for_frontend()

    async def async_remove_device(self, mac: str) -> tuple[list[dict[str, Any]], str]:
        """Remove a device by MAC and persist the complete list."""
        clean_mac = self._normalize_mac(mac)

        async with self._write_lock:
            index = next(
                (
                    index
                    for index, device in enumerate(self._devices)
                    if device["mac"].lower() == clean_mac
                ),
                None,
            )
            if index is None:
                raise ValueError("Nie znaleziono urządzenia")

            removed = self._devices.pop(index)
            removed_presence = self._presence_by_name.pop(removed["name"], None)
            try:
                await self._async_save_devices()
            except OSError:
                self._devices.insert(index, removed)
                self._presence_by_name[removed["name"]] = removed_presence
                raise

        self._notify_listeners()
        return self.devices_for_frontend(), clean_mac

    def presence_for_name(self, name: str) -> bool | None:
        """Return the latest known status for a configured name."""
        return self._presence_by_name.get(name)

    def devices_for_frontend(self) -> list[dict[str, Any]]:
        """Return configured devices and their latest presence state."""
        return [
            {
                "name": device["name"],
                "mac": device["mac"],
                "athome": self._presence_by_name.get(device["name"]),
            }
            for device in self._devices
        ]

    def _set_all_unknown(self) -> None:
        self._presence_by_name = {device["name"]: None for device in self._devices}
        self._notify_listeners()

    @staticmethod
    def _validate_result_item(item: Any) -> tuple[str, bool]:
        if not isinstance(item, dict):
            raise ValueError("result entry must be an object")

        name = item.get("name")
        athome = item.get("athome")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("field 'name' must be a non-empty string")
        if isinstance(athome, bool) or not isinstance(athome, int) or athome not in (0, 1):
            raise ValueError("field 'athome' must be 0 or 1")
        return name.strip(), bool(athome)

    async def _async_load_result(self, *, log_problem: bool = True) -> None:
        """Read wynik.json. Accept the original object format and a result list."""
        presence = {device["name"]: None for device in self._devices}

        try:
            exists = await self.hass.async_add_executor_job(self.result_path.exists)
            if not exists:
                if log_problem:
                    _LOGGER.warning("%s does not exist", self.result_path)
                self._presence_by_name = presence
                self._notify_listeners()
                return

            raw = await self.hass.async_add_executor_job(
                self.result_path.read_text, "utf-8"
            )
            if not raw.strip():
                if log_problem:
                    _LOGGER.warning("%s is empty", RESULT_FILENAME)
                self._presence_by_name = presence
                self._notify_listeners()
                return

            data = json.loads(raw)
            if isinstance(data, dict) and "results" in data:
                items = data["results"]
            elif isinstance(data, list):
                items = data
            else:
                items = [data]

            if not isinstance(items, list):
                raise ValueError("results must be a list")

            for item in items:
                name, athome = self._validate_result_item(item)
                if name in presence:
                    presence[name] = athome

            self._presence_by_name = presence
            self._notify_listeners()
        except (OSError, json.JSONDecodeError, ValueError) as err:
            if log_problem:
                _LOGGER.warning("Cannot read %s: %s", self.result_path, err)
            self._presence_by_name = presence
            self._notify_listeners()

    async def async_refresh_result(self, _now: Any = None) -> None:
        """Read wynik.json without starting any external process."""
        if self._result_lock.locked():
            return

        async with self._result_lock:
            await self._async_load_result()

    async def async_scheduled_scan(self, _now: Any = None) -> None:
        """Backward-compatible alias: only refresh wynik.json."""
        await self.async_refresh_result(_now)

    async def async_stop(self) -> None:
        """Nothing to stop; this version starts no child processes."""
        return
