# Load data
eastie_data <- readRDS("data/Eastie_UFP.rds")

# Filter for August 1st, 2025
august_first <- as.Date("2025-08-01")
eastie_data$date <- as.Date(eastie_data$timestamp)
august_data <- eastie_data %>% 
  filter(date == august_first) %>%
  filter(!is.na(cpc_particle_number_conc_corr.x))

cat("Filtered data for August 1st, 2025:\n")
cat("Total observations:", nrow(august_data), "\n")

if (nrow(august_data) == 0) {
  stop("No data found for August 1st, 2025. Please check the data file.")
}

cat("Time range:", as.character(min(august_data$timestamp)), "to", as.character(max(august_data$timestamp)), "\n")

# Remove any existing lat/lon columns from august_data to avoid conflicts
# (they're likely NA anyway based on the data structure)
august_data <- august_data %>% 
  select(-any_of(c("lat", "lon", "geo.lat", "geo.lon")))

# Merge with sensor coordinates using left_join
sensor_coords_subset <- sensor_coords %>% select(sensor, lat, lon)
august_data <- august_data %>%
  left_join(sensor_coords_subset, by = c("sn.x" = "sensor"))

# Remove rows without coordinates
august_data <- august_data %>% filter(!is.na(lat) & !is.na(lon))

if (nrow(august_data) == 0) {
  stop("No data with valid coordinates found for August 1st, 2025.")
}

# Create time groups (every 5 minutes for smoother animation)
august_data$time_group <- floor_date(august_data$timestamp, "5 minutes")

# Calculate mean pollution for each sensor at each time point
animation_data <- august_data %>%
  group_by(time_group, sn.x, lat, lon) %>%
  summarise(
    pollution = mean(cpc_particle_number_conc_corr.x, na.rm = TRUE),
    n_obs = n(),
    .groups = "drop"
  ) %>%
  filter(n_obs >= 1)

cat("Animation data prepared:", nrow(animation_data), "time-sensor combinations\n")
cat("Unique time points:", length(unique(animation_data$time_group)), "\n")

# Get pollution range for scaling
pollution_min <- min(animation_data$pollution, na.rm = TRUE)
pollution_max <- max(animation_data$pollution, na.rm = TRUE)
cat("Pollution range:", pollution_min, "to", pollution_max, "particles/cm³\n")

# Create output directory
if (!dir.exists("out")) {
  dir.create("out")
  cat("Created output directory: out/\n")
}

# Check if we have animation data
if (nrow(animation_data) == 0) {
  stop("No animation data available. Cannot generate frames.")
}

# Create frames for each time point
unique_times <- sort(unique(animation_data$time_group))
cat("\nGenerating", length(unique_times), "frames...\n")

for (i in seq_along(unique_times)) {
  current_time <- unique_times[i]
  time_data <- animation_data %>% filter(time_group == current_time)
  
  # Create the map background
  map_plot <- create_maps_background(
    sites_data = sensor_coords,
    long_min = lon_min,
    long_max = lon_max,
    lat_min = lat_min,
    lat_max = lat_max
  )
  
  # Add pollution circles with color and size based on pollution level
  # Add circles to the plot
  map_plot <- map_plot +
    geom_point(
      data = time_data,
      aes(x = lon, y = lat, 
          size = pollution, 
          color = pollution),
      alpha = 0.7
    ) +
    scale_size_continuous(
      name = "UFP Concentration\n(particles/cm³)",
      range = c(2, 15),
      breaks = pretty(c(pollution_min, pollution_max), n = 5),
      guide = guide_legend(override.aes = list(alpha = 0.7))
    ) +
    scale_color_viridis_c(
      name = "UFP Concentration\n(particles/cm³)",
      option = "plasma",
      breaks = pretty(c(pollution_min, pollution_max), n = 5),
      guide = guide_colorbar(barwidth = 1, barheight = 10)
    ) +
    labs(
      title = paste("Ultrafine Particle Concentration - August 1, 2025"),
      subtitle = paste("Time:", format(current_time, "%H:%M:%S")),
      x = "Longitude",
      y = "Latitude"
    ) +
    theme(
      plot.title = element_text(size = 14, face = "bold", hjust = 0.5),
      plot.subtitle = element_text(size = 12, hjust = 0.5),
      legend.position = "right",
      legend.box = "vertical",
      legend.title = element_text(size = 10, face = "bold"),
      legend.text = element_text(size = 9)
    )
  
  # Save frame
  frame_filename <- sprintf("out/frame_%04d.png", i)
  ggsave(
    frame_filename,
    plot = map_plot,
    width = 12,
    height = 8,
    dpi = 150  # Good quality for animation frames
  )
  
  if (i %% 10 == 0 || i == length(unique_times)) {
    cat("Progress: ", i, "/", length(unique_times), " frames completed\n")
  }
}

cat("\nAnimation frames saved to out/ folder\n")
cat("Total frames:", length(unique_times), "\n")