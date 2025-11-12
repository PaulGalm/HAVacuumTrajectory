"""Config flow for the vacuum_tracker integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_MAX_POINTS,
    CONF_POSITION_ATTRIBUTE,
    CONF_VACUUMS,
    CONF_X_ATTRIBUTE,
    CONF_Y_ATTRIBUTE,
    DEFAULT_MAX_POINTS,
    DEFAULT_POSITION_ATTRIBUTE,
    DEFAULT_X_ATTRIBUTE,
    DEFAULT_Y_ATTRIBUTE,
    DOMAIN,
)


class VacuumTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration workflow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            data = _normalise_config(user_input)
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured(updates=data)
            return self.async_create_entry(title="Vacuum Tracker", data=data)

        return self.async_show_form(step_id="user", data_schema=_build_schema())

    @staticmethod
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return VacuumTrackerOptionsFlow(entry)


class VacuumTrackerOptionsFlow(config_entries.OptionsFlow):
    """Allow overriding entry options after creation."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict | None = None):
        if user_input is not None:
            data = _normalise_config(user_input)
            return self.async_create_entry(title="", data=data)

        current = {**self._entry.data, **self._entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(current),
        )


def _build_schema(values: dict | None = None) -> vol.Schema:
    """Build a form schema with sensible defaults."""
    values = values or {}
    return vol.Schema(
        {
            vol.Required(CONF_VACUUMS, default=values.get(CONF_VACUUMS, [])): selector.selector(
                {
                    "entity": {
                        "domain": "vacuum",
                        "multiple": True,
                    }
                }
            ),
            vol.Optional(
                CONF_MAX_POINTS,
                default=values.get(CONF_MAX_POINTS, DEFAULT_MAX_POINTS),
            ): selector.selector(
                {
                    "number": {
                        "min": 10,
                        "max": 10000,
                        "step": 10,
                        "mode": "box",
                    }
                }
            ),
            vol.Optional(
                CONF_POSITION_ATTRIBUTE,
                default=values.get(CONF_POSITION_ATTRIBUTE, DEFAULT_POSITION_ATTRIBUTE),
            ): selector.selector({"text": {"type": "text"}}),
            vol.Optional(
                CONF_X_ATTRIBUTE,
                default=values.get(CONF_X_ATTRIBUTE, DEFAULT_X_ATTRIBUTE),
            ): selector.selector({"text": {"type": "text"}}),
            vol.Optional(
                CONF_Y_ATTRIBUTE,
                default=values.get(CONF_Y_ATTRIBUTE, DEFAULT_Y_ATTRIBUTE),
            ): selector.selector({"text": {"type": "text"}}),
        }
    )


def _normalise_config(user_input: dict) -> dict:
    """Ensure list fields are properly structured."""
    vacuums = user_input.get(CONF_VACUUMS, [])
    if isinstance(vacuums, str):
        vacuums = [v.strip() for v in vacuums.split(",") if v.strip()]
    return {
        CONF_VACUUMS: vacuums,
        CONF_MAX_POINTS: user_input.get(CONF_MAX_POINTS, DEFAULT_MAX_POINTS),
        CONF_POSITION_ATTRIBUTE: user_input.get(
            CONF_POSITION_ATTRIBUTE, DEFAULT_POSITION_ATTRIBUTE
        ),
        CONF_X_ATTRIBUTE: user_input.get(CONF_X_ATTRIBUTE, DEFAULT_X_ATTRIBUTE),
        CONF_Y_ATTRIBUTE: user_input.get(CONF_Y_ATTRIBUTE, DEFAULT_Y_ATTRIBUTE),
    }
