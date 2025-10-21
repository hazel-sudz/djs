# Load required packages
library(openair)
library(dplyr)
library(lubridate)
library(ggplot2)
library(gganimate)
library(viridis)
library(scales)
library(ggnewscale)

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

# Create interpolation grid
cat("\nCreating interpolation grid...\n")
grid_resolution <- 50  # Number of grid points in each direction
x_range <- range(sensor_coords$x)
y_range <- range(sensor_coords$y)

# Add some padding around the sensors
x_padding <- (x_range[2] - x_range[1]) * 0.2
y_padding <- (y_range[2] - y_range[1]) * 0.2

grid_x <- seq(x_range[1] - x_padding, x_range[2] + x_padding, length.out = grid_resolution)
grid_y <- seq(y_range[1] - y_padding, y_range[2] + y_padding, length.out = grid_resolution)
grid_points <- expand.grid(x = grid_x, y = grid_y)

cat("Grid created with", nrow(grid_points), "interpolation points\n")

# Function to interpolate pollution and wind using inverse distance weighting
interpolate_data <- function(grid_point, sensor_data, power = 2) {
  # grid_point is a vector with x and y coordinates
  point_x <- grid_point[1]
  point_y <- grid_point[2]
  
  # Calculate distances to all sensors
  distances <- sqrt((point_x - sensor_data$x)^2 + (point_y - sensor_data$y)^2)
  
  # Avoid division by zero
  distances[distances < 1] <- 1
  
  # Calculate weights (inverse distance weighting)
  weights <- 1 / (distances^power)
  
  # Weighted averages
  weighted_pollution <- sum(sensor_data$pollution_mean * weights) / sum(weights)
  weighted_wind_u <- sum(sensor_data$wind_u * weights) / sum(weights)
  weighted_wind_v <- sum(sensor_data$wind_v * weights) / sum(weights)
  weighted_wind_speed <- sum(sensor_data$wind_speed * weights) / sum(weights)
  
  return(c(pollution = weighted_pollution, 
           wind_u = weighted_wind_u, 
           wind_v = weighted_wind_v, 
           wind_speed = weighted_wind_speed))
}

# Create interpolated data for each time group
cat("Interpolating pollution and wind data...\n")
interpolated_data <- data.frame()

for(time_point in unique(animation_summary$time_group)) {
  time_data <- animation_summary[animation_summary$time_group == time_point, ]
  
  if(nrow(time_data) >= 2) {  # Need at least 2 sensors for interpolation
    # Interpolate for each grid point
    grid_results <- apply(grid_points, 1, function(point) {
      interpolate_data(c(point[1], point[2]), time_data)
    })
    
    # Extract results
    grid_pollution <- grid_results["pollution", ]
    grid_wind_u <- grid_results["wind_u", ]
    grid_wind_v <- grid_results["wind_v", ]
    grid_wind_speed <- grid_results["wind_speed", ]
    
    # Create data frame for this time point
    time_interpolated <- data.frame(
      time_group = time_point,
      x = grid_points$x,
      y = grid_points$y,
      pollution_mean = grid_pollution,
      wind_u = grid_wind_u,
      wind_v = grid_wind_v,
      wind_speed = grid_wind_speed,
      interpolated = TRUE
    )
    
    interpolated_data <- rbind(interpolated_data, time_interpolated)
  }
}

cat("Interpolated data created:", nrow(interpolated_data), "grid-time combinations\n")

# Combine sensor data with interpolated data
animation_summary$interpolated <- FALSE
combined_data <- rbind(animation_summary[, c("time_group", "x", "y", "pollution_mean", "wind_u", "wind_v", "wind_speed", "interpolated")], 
                      interpolated_data)

# Create the animation
cat("\nCreating animation...\n")

# Define pollution color scale
pollution_range <- range(combined_data$pollution_mean, na.rm = TRUE)
cat("Pollution range for color scale:", pollution_range[1], "to", pollution_range[2], "particles/cm³\n")

# Create the plot
p <- ggplot(combined_data, aes(x = x, y = y)) +
  # Plot interpolated points as background
  geom_point(data = combined_data[combined_data$interpolated == TRUE, ], 
             aes(color = pollution_mean), 
             size = 1, alpha = 0.6) +
  # Plot sensor points on top
  geom_point(data = combined_data[combined_data$interpolated == FALSE, ], 
             aes(color = pollution_mean, size = pollution_mean), 
             alpha = 0.9) +
  # Add wind vectors (arrows) for interpolated points
  geom_segment(data = combined_data[combined_data$interpolated == TRUE, ], 
               aes(xend = x + wind_u * 200, yend = y + wind_v * 200, 
                   linewidth = wind_speed),
               arrow = arrow(length = unit(0.1, "cm")),
               color = "white", alpha = 0.7) +
  # Add wind vectors for sensor points
  geom_segment(data = combined_data[combined_data$interpolated == FALSE, ], 
               aes(xend = x + wind_u * 300, yend = y + wind_v * 300, 
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
    x = "Longitude (meters from center)",
    y = "Latitude (meters from center)",
    caption = "Data: Quant-AQ sensors | Animation shows 30-minute averages | White/black arrows show wind direction and speed"
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