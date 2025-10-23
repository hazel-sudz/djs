# Load required packages
library(openair)
library(dplyr)
library(lubridate)
library(ggplot2)
library(gganimate)
library(viridis)
library(scales)
library(ggnewscale)
library(ggmap)
library(sf)
library(osmdata)

# Load the Eastie_UFP.rds data
cat("Loading Eastie_UFP.rds data...\n")
eastie_data <- readRDS("Eastie_UFP.rds")


# Check unique sensor names
cat("\nUnique sensor names:\n")
unique_sensors <- unique(eastie_data$sn.x)
print(unique_sensors[!is.na(unique_sensors)])

# Count observations by sensor
cat("\nCount by sensor:\n")
sensor_counts <- table(eastie_data$sn.x, useNA = "ifany")
print(sensor_counts)

# Split data by sensor name
cat("\nSplitting data by sensor...\n")
sensor_data <- split(eastie_data, eastie_data$sn.x)

# Display information about each sensor dataset
for(sensor_name in names(sensor_data)) {
  if(!is.na(sensor_name)) {
    cat("\n=== Sensor:", sensor_name, "===\n")
    cat("Number of observations:", nrow(sensor_data[[sensor_name]]), "\n")
    cat("Date range:", as.character(min(sensor_data[[sensor_name]]$timestamp)), "to", as.character(max(sensor_data[[sensor_name]]$timestamp)), "\n")
    cat("Pollution range:", min(sensor_data[[sensor_name]]$cpc_particle_number_conc_corr.x, na.rm = TRUE), "to", max(sensor_data[[sensor_name]]$cpc_particle_number_conc_corr.x, na.rm = TRUE), "particles/cm³\n")
  }
}

# Create individual data frames for each sensor
sensor_00007 <- sensor_data[["MOD-UFP-00007"]]
sensor_00008 <- sensor_data[["MOD-UFP-00008"]] 
sensor_00009 <- sensor_data[["MOD-UFP-00009"]]

cat("\nData split complete! Individual sensor datasets created:\n")
cat("- sensor_00007:", nrow(sensor_00007), "observations\n")
cat("- sensor_00008:", nrow(sensor_00008), "observations\n") 
cat("- sensor_00009:", nrow(sensor_00009), "observations\n")

# Define sensor coordinates (lat, lon)
sensor_coords <- data.frame(
  sensor = c("MOD-UFP-00007", "MOD-UFP-00008", "MOD-UFP-00009"),
  lat = c(42.36148, 42.38407, 42.36407),
  lon = c(-70.97251, -71.00227, -71.0291),
  stringsAsFactors = FALSE
)

# Calculate center point and bounding box for map
center_lat <- mean(sensor_coords$lat)
center_lon <- mean(sensor_coords$lon)

# Create expanded bounding box to show airport and surrounding area
lat_range <- range(sensor_coords$lat)
lon_range <- range(sensor_coords$lon)

# Much larger padding to show airport and surrounding landmarks
lat_padding <- (lat_range[2] - lat_range[1]) * 2.0  # 2x the sensor spread
lon_padding <- (lon_range[2] - lon_range[1]) * 2.0  # 2x the sensor spread

bbox <- c(
  left = lon_range[1] - lon_padding,
  bottom = lat_range[1] - lat_padding,
  right = lon_range[2] + lon_padding,
  top = lat_range[2] + lat_padding
)

cat("\nSensor coordinates:\n")
print(sensor_coords)
cat("\nCenter point:", center_lat, center_lon, "\n")
cat("Bounding box:", bbox, "\n")

# Get OpenStreetMap data for background
cat("\nGetting OpenStreetMap data...\n")
# Create bounding box for osmdata
bbox_osm <- c(bbox["left"], bbox["bottom"], bbox["right"], bbox["top"])

# Get comprehensive OpenStreetMap data for airport and surrounding area
tryCatch({
  # Get all road types for detailed street network
  roads <- opq(bbox = bbox_osm) %>%
    add_osm_feature(key = "highway", value = c("motorway", "trunk", "primary", "secondary", "tertiary", 
                                               "residential", "unclassified", "service", "track")) %>%
    osmdata_sf()
  
  # Get water features
  water <- opq(bbox = bbox_osm) %>%
    add_osm_feature(key = "natural", value = c("water", "bay", "strait")) %>%
    osmdata_sf()
  
  # Get coastline
  coastline <- opq(bbox = bbox_osm) %>%
    add_osm_feature(key = "natural", value = "coastline") %>%
    osmdata_sf()
  
  # Get airport features
  airport <- opq(bbox = bbox_osm) %>%
    add_osm_feature(key = "aeroway", value = c("runway", "taxiway", "apron", "terminal", "hangar")) %>%
    osmdata_sf()
  
  # Get buildings and landmarks
  buildings <- opq(bbox = bbox_osm) %>%
    add_osm_feature(key = "building") %>%
    osmdata_sf()
  
  # Get points of interest and landmarks
  poi <- opq(bbox = bbox_osm) %>%
    add_osm_feature(key = "amenity", value = c("airport", "hospital", "school", "university", "parking")) %>%
    osmdata_sf()
  
  # Get parks and green spaces
  parks <- opq(bbox = bbox_osm) %>%
    add_osm_feature(key = "leisure", value = c("park", "golf_course", "sports_centre")) %>%
    osmdata_sf()
  
  cat("Comprehensive OpenStreetMap data retrieved successfully\n")
  map_data_available <- TRUE
}, error = function(e) {
  cat("Error getting OpenStreetMap data:", e$message, "\n")
  cat("Proceeding without map background\n")
  map_data_available <- FALSE
})

# Keep original lat/lon coordinates for plotting on map
sensor_coords$x <- sensor_coords$lon
sensor_coords$y <- sensor_coords$lat

cat("Map background obtained successfully\n")

# Prepare data for animation
cat("\nPreparing data for animation...\n")

# Create a combined dataset with all sensors (including wind data)
animation_data <- rbind(
  sensor_00007 %>% select(timestamp, cpc_particle_number_conc_corr.x, sn.x, met.wx_u, met.wx_v, met.wx_ws, met.wx_wd) %>% 
    filter(!is.na(cpc_particle_number_conc_corr.x)) %>%
    mutate(sensor = "MOD-UFP-00007"),
  sensor_00008 %>% select(timestamp, cpc_particle_number_conc_corr.x, sn.x, met.wx_u, met.wx_v, met.wx_ws, met.wx_wd) %>% 
    filter(!is.na(cpc_particle_number_conc_corr.x)) %>%
    mutate(sensor = "MOD-UFP-00008"),
  sensor_00009 %>% select(timestamp, cpc_particle_number_conc_corr.x, sn.x, met.wx_u, met.wx_v, met.wx_ws, met.wx_wd) %>% 
    filter(!is.na(cpc_particle_number_conc_corr.x)) %>%
    mutate(sensor = "MOD-UFP-00009")
)

# Add normalized coordinates
animation_data <- merge(animation_data, sensor_coords[, c("sensor", "x", "y")], by = "sensor")

# Create time groups for animation (every 30 minutes)
animation_data$time_group <- floor_date(animation_data$timestamp, "30 minutes")

# Calculate pollution and wind statistics for each time group and sensor
animation_summary <- animation_data %>%
  group_by(time_group, sensor, x, y) %>%
  summarise(
    pollution_mean = mean(cpc_particle_number_conc_corr.x, na.rm = TRUE),
    pollution_max = max(cpc_particle_number_conc_corr.x, na.rm = TRUE),
    pollution_min = min(cpc_particle_number_conc_corr.x, na.rm = TRUE),
    wind_u = mean(met.wx_u, na.rm = TRUE),
    wind_v = mean(met.wx_v, na.rm = TRUE),
    wind_speed = mean(met.wx_ws, na.rm = TRUE),
    wind_direction = mean(met.wx_wd, na.rm = TRUE),
    n_obs = n(),
    .groups = "drop"
  ) %>%
  filter(n_obs >= 1)  # Only include time groups with data

cat("Animation data prepared:", nrow(animation_summary), "time-sensor combinations\n")
cat("Time range:", as.character(min(animation_summary$time_group)), "to", as.character(max(animation_summary$time_group)), "\n")

# Skip interpolation grid - we'll only show sensor points
cat("\nSkipping interpolation - showing only sensor locations\n")

# Use only sensor data (no interpolation)
animation_summary$interpolated <- FALSE
combined_data <- animation_summary[, c("time_group", "x", "y", "pollution_mean", "wind_u", "wind_v", "wind_speed", "interpolated")]

cat("Using only sensor data:", nrow(combined_data), "sensor-time combinations\n")

# Create the animation
cat("\nCreating animation...\n")

# Define pollution color scale
pollution_range <- range(combined_data$pollution_mean, na.rm = TRUE)
cat("Pollution range for color scale:", pollution_range[1], "to", pollution_range[2], "particles/cm³\n")

# Create the plot with comprehensive OpenStreetMap background - sensor points only
p <- ggplot(combined_data, aes(x = x, y = y)) +
  # Add water features if available
  {if(exists("map_data_available") && map_data_available && !is.null(water$osm_polygons) && nrow(water$osm_polygons) > 0) {
    geom_sf(data = water$osm_polygons, fill = "lightblue", color = NA, alpha = 0.6, inherit.aes = FALSE)
  } else {
    geom_rect(aes(xmin = bbox["left"], xmax = bbox["right"], 
                  ymin = bbox["bottom"], ymax = bbox["top"]), 
              fill = "lightblue", alpha = 0.3, color = "darkblue", linewidth = 1)
  }} +
  # Add coastline if available
  {if(exists("map_data_available") && map_data_available && !is.null(coastline$osm_lines) && nrow(coastline$osm_lines) > 0) {
    geom_sf(data = coastline$osm_lines, color = "darkblue", linewidth = 1, inherit.aes = FALSE)
  }} +
  # Add parks and green spaces
  {if(exists("map_data_available") && map_data_available && !is.null(parks$osm_polygons) && nrow(parks$osm_polygons) > 0) {
    geom_sf(data = parks$osm_polygons, fill = "lightgreen", color = NA, alpha = 0.4, inherit.aes = FALSE)
  }} +
  # Add buildings (light gray)
  {if(exists("map_data_available") && map_data_available && !is.null(buildings$osm_polygons) && nrow(buildings$osm_polygons) > 0) {
    geom_sf(data = buildings$osm_polygons, fill = "lightgray", color = "gray60", linewidth = 0.3, alpha = 0.6, inherit.aes = FALSE)
  }} +
  # Add airport features (runways, taxiways, etc.)
  {if(exists("map_data_available") && map_data_available && !is.null(airport$osm_lines) && nrow(airport$osm_lines) > 0) {
    geom_sf(data = airport$osm_lines, color = "darkgray", linewidth = 1.5, alpha = 0.8, inherit.aes = FALSE)
  }} +
  {if(exists("map_data_available") && map_data_available && !is.null(airport$osm_polygons) && nrow(airport$osm_polygons) > 0) {
    geom_sf(data = airport$osm_polygons, fill = "lightgray", color = "darkgray", linewidth = 0.8, alpha = 0.7, inherit.aes = FALSE)
  }} +
  # Add roads with different styles for different types
  {if(exists("map_data_available") && map_data_available && !is.null(roads$osm_lines) && nrow(roads$osm_lines) > 0) {
    geom_sf(data = roads$osm_lines, color = "gray40", linewidth = 0.3, alpha = 0.8, inherit.aes = FALSE)
  }} +
  # Add points of interest
  {if(exists("map_data_available") && map_data_available && !is.null(poi$osm_points) && nrow(poi$osm_points) > 0) {
    geom_sf(data = poi$osm_points, color = "red", size = 1, alpha = 0.7, inherit.aes = FALSE)
  }} +
  # Plot sensor points only
  geom_point(aes(color = pollution_mean, size = pollution_mean), 
             alpha = 0.9) +
  # Add wind vectors for sensor points
  geom_segment(aes(xend = x + wind_u * 0.002, yend = y + wind_v * 0.002, 
                   linewidth = wind_speed),
               arrow = arrow(length = unit(0.15, "cm")),
               color = "black", alpha = 0.8) +
  scale_color_gradient2(
    name = "Pollution\n(particles/cm³)",
    trans = "log10",
    labels = scales::comma_format(),
    low = "blue",
    mid = "yellow", 
    high = "red",
    midpoint = log10(mean(animation_summary$pollution_mean, na.rm = TRUE))
  ) +
  scale_size_continuous(
    name = "Pollution\n(particles/cm³)",
    trans = "log10",
    range = c(8, 25),
    guide = "none"
  ) +
  scale_linewidth_continuous(
    name = "Wind Speed\n(m/s)",
    range = c(0.5, 3),
    guide = guide_legend(override.aes = list(color = "black"))
  ) +
  labs(
    title = "Ultrafine Particle Pollution in East Boston",
    subtitle = "Time: {frame_time}",
    x = "Longitude",
    y = "Latitude",
    caption = "Data: Quant-AQ sensors | Animation shows 30-minute averages | White/black arrows show wind direction and speed"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold"),
    plot.subtitle = element_text(size = 14),
    axis.title = element_text(size = 12),
    legend.title = element_text(size = 10),
    legend.text = element_text(size = 8),
    panel.grid.minor = element_blank(),
    panel.background = element_rect(fill = "lightblue", color = NA)
  ) +
  coord_sf(xlim = c(bbox["left"], bbox["right"]), 
           ylim = c(bbox["bottom"], bbox["top"]), 
           expand = FALSE) +
  transition_time(time_group) +
  ease_aes('linear')

# Render the animation
cat("Rendering animation (this may take a few minutes)...\n")
total_frames <- length(unique(combined_data$time_group))
target_duration <- 20  # seconds
fps <- total_frames / target_duration

cat("Total frames:", total_frames, "\n")
cat("Target duration:", target_duration, "seconds\n") 
cat("Calculated FPS:", round(fps, 2), "\n")

animated_plot <- animate(
  p,
  nframes = total_frames,
  fps = fps,
  width = 800,
  height = 600,
  renderer = gifski_renderer()
)

# Save the animation
cat("Saving animation...\n")
anim_save("eastie_pollution_animation.gif", animated_plot)

cat("Animation saved as 'eastie_pollution_animation.gif'\n")
cat("Animation complete!\n")