"""Constants for the vacuum_tracker integration."""

from homeassistant.const import Platform

DOMAIN = "vacuum_tracker"
CONF_VACUUMS = "vacuums"
CONF_MAX_POINTS = "max_points"
CONF_POSITION_ATTRIBUTE = "position_attribute"
CONF_X_ATTRIBUTE = "x_attribute"
CONF_Y_ATTRIBUTE = "y_attribute"
DEFAULT_MAX_POINTS = 1000
DEFAULT_POSITION_ATTRIBUTE = "vacuum_tracker_position"
DEFAULT_X_ATTRIBUTE = "x"
DEFAULT_Y_ATTRIBUTE = "y"
PLATFORMS: tuple[Platform, ...] = (Platform.SENSOR,)
