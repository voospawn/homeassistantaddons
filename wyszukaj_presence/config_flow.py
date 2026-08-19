"""Config flow for Wyszukaj Presence."""

from __future__ import annotations

from homeassistant import config_entries

from .const import DOMAIN


class WyszukajPresenceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create the single integration entry."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create the integration without additional configuration."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return self.async_create_entry(title="Obecno\u015b\u0107 urz\u0105dze\u0144", data={})
