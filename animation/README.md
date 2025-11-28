# UFP Animation

Generates animated visualizations of Ultrafine Particle (UFP) sensor data on OpenStreetMap backgrounds.

## Quick Start

```bash
Rscript main.R
```

This will generate:
- Animation frames in `out/frame_XXXX.png`
- Final video at `out/animation.mp4`

## Configuration

Edit the `config` list in `main.R` to customize:

```r
config <- list(
  data_path = "data/Eastie_UFP.rds",  # Path to UFP data
  target_date = "2025-08-01",          # Date to animate
  title_date = "August 1, 2025",       # Title text
  output_dir = "out",                  # Output directory
  seconds_per_frame = 2,               # Video speed (seconds per frame)
  cleanup_frames = FALSE               # Delete frames after video creation
)
```

## Project Structure

```
animation/
├── main.R                 # Entry point - orchestrates the pipeline
├── data/
│   └── Eastie_UFP.rds     # UFP sensor data
├── src/
│   ├── setup.R            # Package management
│   ├── constants.R        # Sensor coordinates and map extent
│   ├── maps.R             # Base map functions
│   ├── plot_elements.R    # Pollution circles and wind arrows
│   ├── data_processing.R  # Data loading and processing
│   ├── video.R            # Video generation
│   └── animate.R          # Frame generation and pipeline
└── out/
    ├── frame_XXXX.png     # Animation frames
    └── animation.mp4      # Final video
```

## Module Overview

### `src/setup.R`
Package management - automatically installs and loads required packages.

### `src/constants.R`
Defines sensor coordinates and calculates map extent with padding.

### `src/maps.R`
- `create_base_map(map_extent)` - Creates base OSM map layer
- `add_sensor_markers(plot, sensor_coords)` - Adds sensor location markers

### `src/plot_elements.R`
- `add_pollution_circles(plot, time_data, pollution_stats)` - Adds colored/sized pollution indicators
- `add_wind_arrow(plot, wind_data, lon_center, lat_center, map_extent)` - Adds wind direction arrow
- `add_frame_labels(plot, current_time, title_date)` - Adds title and timestamp

### `src/data_processing.R`
- `load_ufp_data(file_path)` - Loads RDS data file
- `filter_by_date(data, target_date)` - Filters to specific date
- `merge_with_coordinates(data, sensor_coords)` - Adds lat/lon to data
- `prepare_animation_data(data, time_interval)` - Aggregates by time groups
- `process_data_pipeline(...)` - Runs full data processing

### `src/video.R`
- `create_video_from_frames(frames_dir, output_file, frame_rate)` - Creates MP4 from PNG frames
- `seconds_to_framerate(seconds_per_frame)` - Converts seconds to fps
- `cleanup_frames(frames_dir)` - Removes frame files

### `src/animate.R`
- `create_single_frame(...)` - Generates one animation frame
- `generate_all_frames(...)` - Generates all frames
- `run_animation_pipeline(...)` - Full end-to-end pipeline

## Dependencies

Required R packages (automatically installed):
- ggspatial, ggplot2, gganimate
- dplyr, lubridate
- viridis, scales, ggnewscale
- httr, jsonlite
- av (for video generation)

System dependencies:
- FFmpeg (for video encoding via `av` package)
- GDAL, GEOS, PROJ (for spatial packages)

On macOS with Homebrew:
```bash
brew install ffmpeg gdal geos proj
```

## Customization

### Changing Map Style
In `src/maps.R`, modify `tile_type` in `create_base_map()`:
- `"osm"` - OpenStreetMap (default)
- `"cartolight"` - CartoDB Light
- `"cartodark"` - CartoDB Dark

### Adjusting Pollution Visualization
In `src/plot_elements.R`, modify `add_pollution_circles()`:
- `range = c(2, 15)` - Min/max circle sizes
- `option = "plasma"` - Viridis color palette

### Wind Arrow Scaling
In `src/plot_elements.R`, modify `calculate_wind_arrow()`:
- `max_wind_speed = 6.0` - Expected max wind speed for normalization
- Arrow length is 15% of map extent by default
