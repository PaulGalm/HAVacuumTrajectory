"""Home Assistant integration to track vacuum trajectories."""

from __future__ import annotations

import logging
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from homeassistant.components.vacuum.const import VacuumActivity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MAX_POINTS,
    CONF_POSITION_ATTRIBUTE,
    CONF_VACUUMS,
    DEFAULT_MAX_POINTS,
    DEFAULT_POSITION_ATTRIBUTE,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class VacuumConfig:
    """Configuration for a tracked vacuum."""

    entity_id: str
    display_name: str | None = None


class VacuumHistoryManager:
    """Central store for per-vacuum position histories."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._max_points = self._coerce_int(
            self._get_entry_value(CONF_MAX_POINTS, DEFAULT_MAX_POINTS),
            DEFAULT_MAX_POINTS,
        )
        self._position_attribute = self._get_entry_value(
            CONF_POSITION_ATTRIBUTE, DEFAULT_POSITION_ATTRIBUTE
        ) or None
        self._vacuum_configs: list[VacuumConfig] = self._build_vacuum_configs()
        self._histories: dict[str, deque[dict[str, Any]]] = {
            vacuum.entity_id: deque(maxlen=self._max_points)
            for vacuum in self._vacuum_configs
        }
        self._unsubs: list[Callable[[], None]] = []
        self._sensor_listeners: dict[str, list[Callable[[], None]]] = defaultdict(list)

    async def async_setup(self) -> None:
        """Set up listeners and pre-load initial positions."""
        for vacuum in self._vacuum_configs:
            current_state = self._hass.states.get(vacuum.entity_id)
            if current_state:
                self._append_from_state(vacuum.entity_id, current_state, initial_load=True)
            unsub = async_track_state_change_event(
                self._hass,
                [vacuum.entity_id],
                self._handle_state_event,
            )
            self._unsubs.append(unsub)

    async def async_unload(self) -> None:
        """Tear down listeners and clear references."""
        while self._unsubs:
            unsub = self._unsubs.pop()
            unsub()
        self._sensor_listeners.clear()
        self._histories.clear()

    def _get_entry_value(self, key: str, default: Any) -> Any:
        if key in self._entry.options:
            return self._entry.options[key]
        return self._entry.data.get(key, default)

    def _build_vacuum_configs(self) -> list[VacuumConfig]:
        result: list[VacuumConfig] = []
        for item in self._get_entry_value(CONF_VACUUMS, []):
            if isinstance(item, dict):
                entity_id = item.get("entity_id")
                name = item.get(CONF_NAME)
            else:
                entity_id = item
                name = None
            if not entity_id:
                continue
            result.append(VacuumConfig(entity_id=entity_id, display_name=name))
        return result

    def _coerce_int(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_vacuum_configs(self) -> list[VacuumConfig]:
        """Expose tracked vacuum definitions to platforms."""
        return self._vacuum_configs

    def get_history(self, entity_id: str) -> list[dict[str, Any]]:
        """Return a serialisable copy of the position history."""
        history = self._histories.get(entity_id)
        if not history:
            return []
        return list(history)

    def register_sensor_listener(self, entity_id: str, callback_fn: Callable[[], None]) -> Callable[[], None]:
        """Register a callback to notify sensors when history mutates."""
        listeners = self._sensor_listeners.setdefault(entity_id, [])
        listeners.append(callback_fn)

        def _remove() -> None:
            if callback_fn in listeners:
                listeners.remove(callback_fn)

        return _remove

    @callback
    def _handle_state_event(self, event: Event) -> None:
        new_state: State | None = event.data.get("new_state")
        entity_id: str = event.data["entity_id"]
        if not new_state:
            _LOGGER.debug("State event without new state for %s", entity_id)
            return
        old_state: State | None = event.data.get("old_state")
        reset = self._maybe_reset_history(entity_id, old_state, new_state)
        appended = self._append_from_state(entity_id, new_state)
        if appended or reset:
            self._notify_listeners(entity_id)

    def _append_from_state(
        self, entity_id: str, state: State, *, initial_load: bool = False
    ) -> bool:
        history = self._histories.get(entity_id)
        if history is None:
            return False
        point = self._extract_point(state)
        if point is None:
            if not initial_load:
                _LOGGER.debug("No valid coordinates found for %s", entity_id)
            return False
        if history and history[-1]["x"] == point["x"] and history[-1]["y"] == point["y"]:
            # Replace the trailing entry to keep the latest timestamp without duplicating points.
            history[-1] = point
            return True
        history.append(point)
        return True

    def _extract_point(self, state: State) -> dict[str, Any] | None:
        # Try a vector attribute first, fallback to separate axes.
        candidate = None
        if self._position_attribute:
            candidate = state.attributes.get(self._position_attribute)
        if candidate is None:
            candidate = state.attributes.get("position")

        coords = self._normalise_coordinates(candidate)
        if coords:
            return {
                "x": coords[0],
                "y": coords[1],
                "timestamp": dt_util.utcnow().isoformat(),
            }

    def _notify_listeners(self, entity_id: str) -> None:
        for listener in list(self._sensor_listeners.get(entity_id, [])):
            listener()

    def _maybe_reset_history(
        self, entity_id: str, old_state: State | None, new_state: State
    ) -> bool:
        if old_state is None:
            return False
        old_status = old_state.state
        new_status = new_state.state
        if old_status is None or new_status is None:
            return False
        try:
            old_activity = VacuumActivity(old_status)
            new_activity = VacuumActivity(new_status)
        except ValueError:
            return False
        if (
            old_activity is VacuumActivity.DOCKED
            and new_activity is VacuumActivity.CLEANING
            and (history := self._histories.get(entity_id)) is not None
        ):
            history.clear()
            _LOGGER.debug(
                "Reset history for %s on docked→cleaning transition", entity_id
            )
            return True
        return False

    def _normalise_coordinates(self, value: Any) -> tuple[float, float] | None:
        """Extract x/y floats from various attribute formats."""
        if value is None:
            return None

        if isinstance(value, (list, tuple, set)):
            iterable: Iterable[Any] = value
        elif isinstance(value, dict):
            iterable = (
                value.get("x"),
                value.get("y"),
            )
        elif isinstance(value, str):
            stripped = value.strip().strip("[]{}()").replace(";", ",")
            matches = re.findall(r"[-+]?[0-9]*\.?[0-9]+", stripped)
            if len(matches) < 2:
                return None
            iterable = (matches[0], matches[1])
        else:
            return None

        try:
            iterator = iter(iterable)
            x_raw = next(iterator)
            y_raw = next(iterator)
        except StopIteration:
            return None

        try:
            return float(x_raw), float(y_raw)
        except (TypeError, ValueError):
            return None


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration via YAML (placeholder)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stub the integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    manager = VacuumHistoryManager(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = manager
    await manager.async_setup()
    if not manager.get_vacuum_configs():
        _LOGGER.warning(
            "vacuum_tracker entry %s has no vacuums configured", entry.entry_id
        )
    _LOGGER.info(
        "Setting up vacuum_tracker for %d vacuum(s)",
        len(manager.get_vacuum_configs()),
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of a config entry."""
    manager: VacuumHistoryManager = hass.data[DOMAIN][entry.entry_id]
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        _LOGGER.info("Unloaded vacuum_tracker entry %s", entry.entry_id)
        await manager.async_unload()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options/settings change."""
    await hass.config_entries.async_reload(entry.entry_id)
