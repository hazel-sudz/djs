# =============================================================================
# Base Map Functions
# =============================================================================
# Functions for creating the base map layer with OpenStreetMap tiles.

# Create base map with OpenStreetMap tiles
# @param map_extent List with lon_min, lon_max, lat_min, lat_max
# @param tile_type Type of map tiles (default: "osm" for OpenStreetMap)
# @param zoom_adjust Zoom adjustment for tile resolution (default: 1)
# @return ggplot object with base map tiles and minimal theme
create_base_map <- function(map_extent, tile_type = "osm", zoom_adjust = 1) {
  ggplot() +
    annotation_map_tile(type = tile_type, zoomin = zoom_adjust) +
    coord_sf(
      xlim = c(map_extent$lon_min, map_extent$lon_max),
      ylim = c(map_extent$lat_min, map_extent$lat_max),
      crs = 4326
    ) +
    xlab("Longitude") +
    ylab("Latitude") +
    theme_minimal() +
    theme(
      panel.grid.major = element_line(color = "gray90", linewidth = 0.3),
      panel.grid.minor = element_line(color = "gray95", linewidth = 0.2),
      axis.text = element_text(size = 10),
      axis.title = element_text(size = 11, face = "bold"),
      plot.title = element_text(size = 12, face = "bold"),
      text = element_text(family = "sans", color = "black"),
      panel.background = element_rect(fill = "white", color = NA),
      plot.background = element_rect(fill = "white", color = NA)
    )
}

# Add sensor location markers to a map
# @param plot ggplot object
# @param sensor_coords Data frame with sensor coordinates (lat, lon)
# @param point_color Color for sensor markers
# @param point_size Size of sensor markers
# @return ggplot object with sensor markers added
add_sensor_markers <- function(plot, sensor_coords, point_color = "red", point_size = 3) {
  plot +
    geom_point(
      data = sensor_coords,
      aes(x = lon, y = lat),
      color = point_color,
      size = point_size
    )
}

# Create complete base map with sensor markers (convenience function)
# @param sensor_coords Data frame with sensor coordinates
# @param map_extent List with lon_min, lon_max, lat_min, lat_max
# @param point_color Color for sensor markers
# @param point_size Size of sensor markers
# @return ggplot object with base map and sensor markers
create_map_with_sensors <- function(sensor_coords, map_extent,
                                     point_color = "red", point_size = 3) {
  base_map <- create_base_map(map_extent)
  add_sensor_markers(base_map, sensor_coords, point_color, point_size)
}

# Legacy function for backwards compatibility
# @deprecated Use create_base_map() and add_sensor_markers() instead
create_maps_background <- function(sites_data,
                                    point_color = "red",
                                    point_size = 3,
                                    long_min = -71.1,
                                    long_max = -70.9,
                                    lat_min = 42.3,
                                    lat_max = 42.45) {
  map_extent <- list(
    lon_min = long_min,
    lon_max = long_max,
    lat_min = lat_min,
    lat_max = lat_max
  )
  create_map_with_sensors(sites_data, map_extent, point_color, point_size)
}
