# Vacuum Tracker

Custom Home Assistant integration for tracking 2D trajectories of vacuum cleaners and exposing them via sensor entities and a custom Lovelace card.

## Installation

1. Copy `custom_components/vacuum_tracker` into your Home Assistant `custom_components` folder.
2. Copy `www/vacuum-path-card.js` into the `www` folder of your Home Assistant configuration (create it if missing) and add it as a Lovelace resource.

```
url: /local/vacuum-path-card.js
type: module
```

## Configuration

Use the Home Assistant UI to add the *Vacuum Tracker* integration. Select the vacuums you want to monitor and adjust the maximum number of stored locations or override the position attribute name if necessary. By default the integration reads coordinates from the `position` attribute and interprets the first two values as `x`/`y`.

The integration creates one sensor per vacuum. Each sensor stores a `history` attribute containing a list of `{x, y, timestamp}` dictionaries representing the recorded trajectory. The sensor state is the number of stored points.

### Lovelace Card

Add the custom card to your dashboard to visualise the path:

```
type: custom:vacuum-path-card
entity: sensor.robot_vacuum_path
line_color: '#00bcd4'
point_color: '#ff9800'
line_width: 3
show_points: false
background: '#000000'
background_image: /local/floorplan.png
scale: 1.2
rotation: -5
offset_x: -2
offset_y: 4
invert_y: false
```

All visual parameters are optional. When `background_image` is provided, the trajectory is drawn over the image with the optional `scale`, `rotation` (degrees), and `offset_x`/`offset_y` (coordinate offsets) applied before rendering. Set `invert_y` to `false` if your background uses a top-left origin.

The integration automatically clears the stored trajectory whenever a tracked vacuum transitions from the docked state to cleaning so each run starts fresh.
