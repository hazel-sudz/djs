# Load required packages
library(openair)
library(dplyr)
library(lubridate)
library(ggplot2)
library(gganimate)
library(viridis)
library(scales)

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

# Calculate center point for normalization
center_lat <- mean(sensor_coords$lat)
center_lon <- mean(sensor_coords$lon)

cat("\nSensor coordinates:\n")
print(sensor_coords)
cat("\nCenter point:", center_lat, center_lon, "\n")

# Convert coordinates to relative positions (normalized around center)
# Convert lat/lon to approximate meters (rough approximation for small area)
lat_to_meters <- 111000  # meters per degree latitude
lon_to_meters <- 111000 * cos(center_lat * pi / 180)  # meters per degree longitude

sensor_coords$x <- (sensor_coords$lon - center_lon) * lon_to_meters
sensor_coords$y <- (sensor_coords$lat - center_lat) * lat_to_meters

cat("\nNormalized sensor positions (meters from center):\n")
print(sensor_coords[, c("sensor", "x", "y")])

# Prepare data for animation
cat("\nPreparing data for animation...\n")

# Create a combined dataset with all sensors
animation_data <- rbind(
  sensor_00007 %>% select(timestamp, cpc_particle_number_conc_corr.x, sn.x) %>% 
    filter(!is.na(cpc_particle_number_conc_corr.x)) %>%
    mutate(sensor = "MOD-UFP-00007"),
  sensor_00008 %>% select(timestamp, cpc_particle_number_conc_corr.x, sn.x) %>% 
    filter(!is.na(cpc_particle_number_conc_corr.x)) %>%
    mutate(sensor = "MOD-UFP-00008"),
  sensor_00009 %>% select(timestamp, cpc_particle_number_conc_corr.x, sn.x) %>% 
    filter(!is.na(cpc_particle_number_conc_corr.x)) %>%
    mutate(sensor = "MOD-UFP-00009")
)

# Add normalized coordinates
animation_data <- merge(animation_data, sensor_coords[, c("sensor", "x", "y")], by = "sensor")

# Create time groups for animation (every 30 minutes)
animation_data$time_group <- floor_date(animation_data$timestamp, "30 minutes")

# Calculate pollution statistics for each time group and sensor
animation_summary <- animation_data %>%
  group_by(time_group, sensor, x, y) %>%
  summarise(
    pollution_mean = mean(cpc_particle_number_conc_corr.x, na.rm = TRUE),
    pollution_max = max(cpc_particle_number_conc_corr.x, na.rm = TRUE),
    pollution_min = min(cpc_particle_number_conc_corr.x, na.rm = TRUE),
    n_obs = n(),
    .groups = "drop"
  ) %>%
  filter(n_obs >= 1)  # Only include time groups with data

cat("Animation data prepared:", nrow(animation_summary), "time-sensor combinations\n")
cat("Time range:", as.character(min(animation_summary$time_group)), "to", as.character(max(animation_summary$time_group)), "\n")

# Create the animation
cat("\nCreating animation...\n")

# Define pollution color scale
pollution_range <- range(animation_summary$pollution_mean, na.rm = TRUE)
cat("Pollution range for color scale:", pollution_range[1], "to", pollution_range[2], "particles/cm³\n")

# Create the plot
p <- ggplot(animation_summary, aes(x = x, y = y)) +
  geom_point(aes(color = pollution_mean, size = pollution_mean), alpha = 0.8) +
  scale_color_viridis_c(
    name = "Pollution\n(particles/cm³)",
    trans = "log10",
    labels = scales::comma_format(),
    option = "plasma"
  ) +
  scale_size_continuous(
    name = "Pollution\n(particles/cm³)",
    trans = "log10",
    range = c(3, 15),
    guide = "none"
  ) +
  labs(
    title = "Ultrafine Particle Pollution in East Boston",
    subtitle = "Time: {frame_time}",
    x = "Longitude (meters from center)",
    y = "Latitude (meters from center)",
    caption = "Data: Quant-AQ sensors | Animation shows 30-minute averages"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold"),
    plot.subtitle = element_text(size = 14),
    axis.title = element_text(size = 12),
    legend.title = element_text(size = 10),
    legend.text = element_text(size = 8),
    panel.grid.minor = element_blank()
  ) +
  coord_fixed(ratio = 1) +
  transition_time(time_group) +
  ease_aes('linear')

# Render the animation
cat("Rendering animation (this may take a few minutes)...\n")
animated_plot <- animate(
  p,
  nframes = length(unique(animation_summary$time_group)),
  fps = 2,
  width = 800,
  height = 600,
  renderer = gifski_renderer()
)

# Save the animation
cat("Saving animation...\n")
anim_save("eastie_pollution_animation.gif", animated_plot)

cat("Animation saved as 'eastie_pollution_animation.gif'\n")
cat("Animation complete!\n")