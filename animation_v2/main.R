source ("src/setup.R")

# Define sensor coordinates (lat, lon)
sensor_coords <- data.frame(
  sensor = c("MOD-UFP-00007", "MOD-UFP-00008", "MOD-UFP-00009"),
  lat = c(42.36148, 42.38407, 42.36407),
  lon = c(-70.97251, -71.00227, -71.0291),
  stringsAsFactors = FALSE
)

# Calculate map extent from sensor coordinates with proper centering and padding
lat_center <- mean(sensor_coords$lat)
lon_center <- mean(sensor_coords$lon)
lat_range <- max(sensor_coords$lat) - min(sensor_coords$lat)
lon_range <- max(sensor_coords$lon) - min(sensor_coords$lon)

# Add padding (20% of the range or minimum 0.01 degrees)
lat_padding <- max(0.01, lat_range * 0.2)
lon_padding <- max(0.01, lon_range * 0.2)

lat_min <- lat_center - lat_range/2 - lat_padding
lat_max <- lat_center + lat_range/2 + lat_padding
lon_min <- lon_center - lon_range/2 - lon_padding
lon_max <- lon_center + lon_range/2 + lon_padding

# Print calculated coordinates for debugging
cat("Sensor coordinates:\n")
print(sensor_coords)
cat("\nCalculated map extent:\n")
cat("Latitude range:", lat_min, "to", lat_max, "\n")
cat("Longitude range:", lon_min, "to", lon_max, "\n")
cat("Center point:", lat_center, ",", lon_center, "\n\n")

# Function to create map with study sites using ggspatial
create_cape_point_map <- function(sites_data, 
                                  point_color = "red",
                                  point_size = 3) {
  
  # Create the plot with OpenStreetMap tiles
  map_plot <- ggplot() +
    annotation_map_tile(type = "osm", zoomin = 1) +
    geom_point(data = sites_data, 
               aes(x = lon, y = lat), 
               color = point_color, 
               size = point_size) +
    coord_sf(xlim = c(-71.1, -70.9),
             ylim = c(42.3, 42.45),
             crs = 4326) +
    xlab("Longitude") + 
    ylab("Latitude") +
    theme_minimal() +
    theme(
      # Enhance plot sharpness
      panel.grid.major = element_line(color = "gray90", linewidth = 0.3),
      panel.grid.minor = element_line(color = "gray95", linewidth = 0.2),
      axis.text = element_text(size = 10),
      axis.title = element_text(size = 11, face = "bold"),
      plot.title = element_text(size = 12, face = "bold"),
      # Improve text rendering
      text = element_text(family = "sans", color = "black"),
      # Remove background for cleaner look
      panel.background = element_rect(fill = "white", color = NA),
      plot.background = element_rect(fill = "white", color = NA)
    )
  
  return(map_plot)
}

# Create and display the map
cape_point_map <- create_cape_point_map(sites_data = sensor_coords)
cape_point_map

# Save at high resolution (1080p equivalent at 600 DPI)
ggsave(
  "eastie_map_highres.png",
  plot = cape_point_map,
  width = 12,
  height = 8,
  dpi = 600  # higher DPI = sharper tiles
)