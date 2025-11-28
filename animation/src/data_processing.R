# =============================================================================
# Data Processing Functions
# =============================================================================
# Functions for loading, filtering, and preparing UFP sensor data for animation.

# Load raw UFP data from RDS file
# @param file_path Path to the RDS file containing UFP data
# @return Data frame with raw UFP measurements
load_ufp_data <- function(file_path = "data/Eastie_UFP.rds") {
  if (!file.exists(file_path)) {
    stop(paste("Data file not found:", file_path))
  }
  readRDS(file_path)
}

# Filter data for a specific date
# @param data Raw UFP data frame
# @param target_date Date to filter for (Date object or string "YYYY-MM-DD")
# @return Filtered data frame for the specified date
filter_by_date <- function(data, target_date) {
  target_date <- as.Date(target_date)
  data$date <- as.Date(data$timestamp)

  filtered <- data %>%
    filter(date == target_date) %>%
    filter(!is.na(cpc_particle_number_conc_corr.x))

  if (nrow(filtered) == 0) {
    stop(paste("No data found for date:", target_date))
  }

  cat("Filtered data for", as.character(target_date), ":\n")
  cat("Total observations:", nrow(filtered), "\n")
  cat("Time range:", as.character(min(filtered$timestamp)),
      "to", as.character(max(filtered$timestamp)), "\n")

  filtered
}

# Merge UFP data with sensor coordinates
# @param data UFP data frame
# @param sensor_coords Data frame with sensor coordinates (sensor, lat, lon)
# @return Data frame with coordinates merged in
merge_with_coordinates <- function(data, sensor_coords) {
  # Remove any existing lat/lon columns to avoid conflicts
  data <- data %>%
    select(-any_of(c("lat", "lon", "geo.lat", "geo.lon")))

  # Merge with sensor coordinates
  sensor_coords_subset <- sensor_coords %>% select(sensor, lat, lon)
  data <- data %>%
    left_join(sensor_coords_subset, by = c("sn.x" = "sensor"))

  # Remove rows without coordinates
  data <- data %>% filter(!is.na(lat) & !is.na(lon))

  if (nrow(data) == 0) {
    stop("No data with valid coordinates found after merging.")
  }

  data
}

# Prepare animation data by aggregating measurements into time groups
# @param data UFP data with coordinates
# @param time_interval Interval for grouping (e.g., "5 minutes")
# @return List with animation_data and wind_summary data frames
prepare_animation_data <- function(data, time_interval = "5 minutes") {
  # Create time groups
  data$time_group <- floor_date(data$timestamp, time_interval)

  # Calculate mean pollution and wind for each sensor at each time point
  animation_data <- data %>%
    group_by(time_group, sn.x, lat, lon) %>%
    summarise(
      pollution = mean(cpc_particle_number_conc_corr.x, na.rm = TRUE),
      wind_u = mean(met.wx_u, na.rm = TRUE),
      wind_v = mean(met.wx_v, na.rm = TRUE),
      wind_speed = mean(met.wx_ws, na.rm = TRUE),
      wind_dir = mean(met.wx_wd, na.rm = TRUE),
      n_obs = n(),
      .groups = "drop"
    ) %>%
    filter(n_obs >= 1)

  # Calculate average wind across all sensors for each time point
  wind_summary <- data %>%
    group_by(time_group) %>%
    summarise(
      avg_wind_u = mean(met.wx_u, na.rm = TRUE),
      avg_wind_v = mean(met.wx_v, na.rm = TRUE),
      avg_wind_speed = mean(met.wx_ws, na.rm = TRUE),
      avg_wind_dir = mean(met.wx_wd, na.rm = TRUE),
      .groups = "drop"
    )

  cat("Animation data prepared:", nrow(animation_data), "time-sensor combinations\n")
  cat("Unique time points:", length(unique(animation_data$time_group)), "\n")

  list(
    animation_data = animation_data,
    wind_summary = wind_summary
  )
}

# Calculate pollution statistics for consistent scaling across frames
# @param animation_data Prepared animation data
# @return List with min, max, and legend breaks
calculate_pollution_stats <- function(animation_data) {
  pollution_min <- min(animation_data$pollution, na.rm = TRUE)
  pollution_max <- max(animation_data$pollution, na.rm = TRUE)
  pollution_breaks <- pretty(c(pollution_min, pollution_max), n = 5)

  cat("Pollution range:", pollution_min, "to", pollution_max, "particles/cm³\n")
  cat("Legend breaks:", paste(pollution_breaks, collapse = ", "), "\n")

  list(
    min = pollution_min,
    max = pollution_max,
    breaks = pollution_breaks
  )
}

# Full data processing pipeline
# @param data_path Path to RDS data file
# @param target_date Date to process
# @param sensor_coords Sensor coordinates data frame
# @param time_interval Time grouping interval
# @return List with all processed data needed for animation
process_data_pipeline <- function(data_path, target_date, sensor_coords,
                                   time_interval = "5 minutes") {
  cat("\n=== Data Processing Pipeline ===\n")

  # Load and filter data
  raw_data <- load_ufp_data(data_path)
  filtered_data <- filter_by_date(raw_data, target_date)

  # Merge with coordinates
  data_with_coords <- merge_with_coordinates(filtered_data, sensor_coords)

  # Prepare animation data
  prepared <- prepare_animation_data(data_with_coords, time_interval)

  # Calculate statistics
  stats <- calculate_pollution_stats(prepared$animation_data)

  cat("=== Data Processing Complete ===\n\n")

  list(
    animation_data = prepared$animation_data,
    wind_summary = prepared$wind_summary,
    pollution_stats = stats,
    unique_times = sort(unique(prepared$animation_data$time_group))
  )
}
