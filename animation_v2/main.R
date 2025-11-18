source ("src/setup.R")
source ("src/constants.R")
source ("src/maps.R")


# Create and display the map
cape_point_map <- create_maps_background(sites_data = sensor_coords)
cape_point_map

# Save at high resolution (1080p equivalent at 600 DPI)
ggsave(
  "eastie_map_highres.png",
  plot = cape_point_map,
  width = 12,
  height = 8,
  dpi = 600  # higher DPI = sharper tiles
)
