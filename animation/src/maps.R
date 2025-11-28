# Function to create map with study sites using ggspatial
create_maps_background <- function(sites_data, 
                                  point_color = "red",
                                  point_size = 3,
                                  long_min = -71.1,
                                  long_max = -70.9,
                                  lat_min = 42.3,
                                  lat_max = 42.45
                                  ) {
  
  # Create the plot with OpenStreetMap tiles
  map_plot <- ggplot() +
    annotation_map_tile(type = "osm", zoomin = 1) +
    geom_point(data = sites_data, 
               aes(x = lon, y = lat), 
               color = point_color, 
               size = point_size) +
    coord_sf(xlim = c(long_min, long_max),
             ylim = c(lat_min, lat_max),
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