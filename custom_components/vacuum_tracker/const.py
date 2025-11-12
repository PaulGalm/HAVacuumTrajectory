"""Constants for the vacuum_tracker integration."""

from homeassistant.const import Platform

DOMAIN = "vacuum_tracker"
CONF_VACUUMS = "vacuums"
CONF_MAX_POINTS = "max_points"
CONF_POSITION_ATTRIBUTE = "position_attribute"
DEFAULT_MAX_POINTS = 1000
DEFAULT_POSITION_ATTRIBUTE = "position"
PLATFORMS: tuple[Platform, ...] = (Platform.SENSOR,)
