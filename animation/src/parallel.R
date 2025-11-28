# =============================================================================
# Parallel Processing Functions
# =============================================================================
# Functions for parallel frame generation using multiple CPU cores.

# Detect number of available CPU cores
# @return Number of cores available for parallel processing
detect_cores <- function() {
  cores <- parallel::detectCores(logical = TRUE)
  cat("Detected", cores, "CPU cores\n")
  cores
}

# Generate frames in parallel using all available cores
# @param unique_times Vector of unique time points
# @param animation_data Full animation dataset
# @param wind_summary Wind summary dataset
# @param sensor_coords Sensor coordinates
# @param map_extent Map extent list
# @param pollution_stats Pollution statistics for scaling
# @param output_dir Output directory for frames
# @param title_date Date string for titles
# @param n_cores Number of cores to use (NULL = auto-detect)
# @return Vector of generated frame file paths
generate_frames_parallel <- function(unique_times, animation_data, wind_summary,
                                      sensor_coords, map_extent, pollution_stats,
                                      output_dir = "out", title_date = "August 1, 2025",
                                      n_cores = NULL) {
  # Detect cores if not specified
  if (is.null(n_cores)) {
    n_cores <- detect_cores()
  }

  # Use n_cores - 1 to leave one core free for system, minimum 1
  n_workers <- max(1, n_cores - 1)
  cat("Using", n_workers, "worker cores for parallel processing\n")

  n_frames <- length(unique_times)
  cat("Generating", n_frames, "frames in parallel...\n")

  # Create cluster
  cl <- parallel::makeCluster(n_workers)

  # Export required objects and functions to cluster
  parallel::clusterExport(cl, c(
    "animation_data", "wind_summary", "sensor_coords", "map_extent",
    "pollution_stats", "output_dir", "title_date", "unique_times"
  ), envir = environment())

  # Load required packages on each worker
  parallel::clusterEvalQ(cl, {
    suppressPackageStartupMessages({
      library(ggplot2)
      library(ggspatial)
      library(dplyr)
      library(viridis)
      library(scales)
    })
  })

  # Export all the plotting functions to workers
  parallel::clusterExport(cl, c(
    "create_base_map",
    "add_wind_arrow",
    "add_pollution_circles",
    "add_pollution_labels",
    "add_frame_labels",
    "calculate_wind_arrow",
    "format_pollution_label"
  ), envir = globalenv())

  # Define the worker function
  generate_single_frame_worker <- function(i) {
    current_time <- unique_times[i]

    # Filter data for current time
    time_data <- animation_data %>% filter(time_group == current_time)
    wind_data <- wind_summary %>% filter(time_group == current_time)

    # Calculate map center
    lon_center <- (map_extent$lon_min + map_extent$lon_max) / 2
    lat_center <- (map_extent$lat_min + map_extent$lat_max) / 2

    # Build the frame layer by layer
    frame_plot <- create_base_map(map_extent)
    frame_plot <- add_wind_arrow(frame_plot, wind_data, lon_center, lat_center, map_extent)
    frame_plot <- add_pollution_circles(frame_plot, time_data, pollution_stats)
    frame_plot <- add_pollution_labels(frame_plot, time_data)
    frame_plot <- add_frame_labels(frame_plot, current_time, title_date)

    # Save frame
    filename <- sprintf("%s/frame_%04d.png", output_dir, i)
    ggsave(filename, plot = frame_plot, width = 12, height = 8, dpi = 150,
           bg = "white")

    filename
  }

  # Export the worker function
  parallel::clusterExport(cl, "generate_single_frame_worker", envir = environment())

  # Track progress with a simple counter
  start_time <- Sys.time()

  # Run in parallel with progress reporting
  frame_files <- parallel::parLapply(cl, seq_along(unique_times), function(i) {
    generate_single_frame_worker(i)
  })

  # Stop cluster
  parallel::stopCluster(cl)

  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
  cat("Completed", n_frames, "frames in", round(elapsed, 1), "seconds\n")
  cat("Average:", round(elapsed / n_frames, 2), "seconds per frame\n")

  unlist(frame_files)
}
