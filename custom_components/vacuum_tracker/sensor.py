"""Sensor platform for the vacuum_tracker integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import VacuumHistoryManager, VacuumConfig
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Configure sensors for each tracked vacuum."""
    manager: VacuumHistoryManager = hass.data[DOMAIN][entry.entry_id]
    sensors = [
        VacuumPathSensor(manager, entry.entry_id, vacuum)
        for vacuum in manager.get_vacuum_configs()
    ]
    async_add_entities(sensors)


class VacuumPathSensor(SensorEntity):
    """Expose a vacuum's movement history as a sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self, manager: VacuumHistoryManager, entry_id: str, config: VacuumConfig
    ) -> None:
        self._manager = manager
        self._entry_id = entry_id
        self._config = config
        self._attr_unique_id = f"{entry_id}_{config.entity_id}_path"
        self._attr_translation_key = "vacuum_path"
        self._attr_icon = "mdi:robot-vacuum"
        self._remove_listener = None

    async def async_added_to_hass(self) -> None:
        """Register for history updates and prime the name."""
        self._remove_listener = self._manager.register_sensor_listener(
            self._config.entity_id, self.async_write_ha_state
        )
        self.async_on_remove(self._remove_listener)
        if self._config.display_name:
            self._attr_name = self._config.display_name
        else:
            source_state = self.hass.states.get(self._config.entity_id)
            if source_state:
                self._attr_name = f"{source_state.name} Path"
            else:
                self._attr_name = f"{self._config.entity_id} Path"
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners on removal."""
        self._remove_listener = None

    @property
    def native_value(self) -> int:
        """Return the number of recorded points."""
        return len(self._manager.get_history(self._config.entity_id))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the recorded path as an attribute."""
        return {"history": self._manager.get_history(self._config.entity_id)}

    async def async_update(self) -> None:
        """Manual refresh hook retained for compatibility."""
        # History updates arrive via push callbacks, so nothing to pull here.
        return
