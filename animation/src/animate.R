# =============================================================================
# Animation Frame Generation
# =============================================================================
# Functions for generating individual animation frames and running the full pipeline.

# Generate a single animation frame
# @param time_index Index of the current time point
# @param current_time POSIXct timestamp for this frame
# @param animation_data Full animation dataset
# @param wind_summary Wind summary dataset
# @param sensor_coords Sensor coordinates
# @param map_extent Map extent list (lon_min, lon_max, lat_min, lat_max)
# @param pollution_stats Pollution statistics for scaling
# @param title_date Date string for title
# @return ggplot object for this frame
create_single_frame <- function(time_index, current_time, animation_data, wind_summary,
                                 sensor_coords, map_extent, pollution_stats,
                                 title_date = "August 1, 2025") {
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

  frame_plot
}

# Save a frame to disk
# @param plot ggplot object
# @param frame_number Frame number for filename
# @param output_dir Output directory
# @param width Plot width in inches
# @param height Plot height in inches
# @param dpi Resolution in DPI
# @return Path to saved file
save_frame <- function(plot, frame_number, output_dir = "out",
                        width = 12, height = 8, dpi = 150) {
  filename <- sprintf("%s/frame_%04d.png", output_dir, frame_number)
  ggsave(filename, plot = plot, width = width, height = height, dpi = dpi,
         bg = "white", device = ragg::agg_png)
  filename
}

# Generate all animation frames (sequential version)
# @param processed_data Output from process_data_pipeline()
# @param sensor_coords Sensor coordinates data frame
# @param map_extent Map extent list
# @param output_dir Output directory for frames
# @param title_date Date string for frame titles
# @return Vector of generated frame file paths
generate_all_frames_sequential <- function(processed_data, sensor_coords, map_extent,
                                            output_dir = "out", title_date = "August 1, 2025") {
  unique_times <- processed_data$unique_times
  n_frames <- length(unique_times)

  cat("Generating", n_frames, "frames sequentially...\n")

  frame_files <- character(n_frames)

  for (i in seq_along(unique_times)) {
    current_time <- unique_times[i]

    # Create and save frame
    frame_plot <- create_single_frame(
      time_index = i,
      current_time = current_time,
      animation_data = processed_data$animation_data,
      wind_summary = processed_data$wind_summary,
      sensor_coords = sensor_coords,
      map_extent = map_extent,
      pollution_stats = processed_data$pollution_stats,
      title_date = title_date
    )

    frame_files[i] <- save_frame(frame_plot, i, output_dir)

    # Progress reporting
    if (i %% 10 == 0 || i == n_frames) {
      cat("Progress:", i, "/", n_frames, "frames completed\n")
    }
  }

  frame_files
}

# Generate all animation frames (with optional parallel processing)
# @param processed_data Output from process_data_pipeline()
# @param sensor_coords Sensor coordinates data frame
# @param map_extent Map extent list
# @param output_dir Output directory for frames
# @param title_date Date string for frame titles
# @param parallel Use parallel processing (TRUE/FALSE)
# @param n_cores Number of cores for parallel processing (NULL = auto-detect)
# @return Vector of generated frame file paths
generate_all_frames <- function(processed_data, sensor_coords, map_extent,
                                 output_dir = "out", title_date = "August 1, 2025",
                                 parallel = TRUE, n_cores = NULL) {
  # Ensure output directory exists
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
    cat("Created output directory:", output_dir, "\n")
  }

  cat("\n=== Frame Generation ===\n")

  if (parallel) {
    # Use parallel processing
    frame_files <- generate_frames_parallel(
      unique_times = processed_data$unique_times,
      animation_data = processed_data$animation_data,
      wind_summary = processed_data$wind_summary,
      sensor_coords = sensor_coords,
      map_extent = map_extent,
      pollution_stats = processed_data$pollution_stats,
      output_dir = output_dir,
      title_date = title_date,
      n_cores = n_cores
    )
  } else {
    # Use sequential processing
    frame_files <- generate_all_frames_sequential(
      processed_data = processed_data,
      sensor_coords = sensor_coords,
      map_extent = map_extent,
      output_dir = output_dir,
      title_date = title_date
    )
  }

  cat("=== Frame Generation Complete ===\n")
  cat("Frames saved to:", output_dir, "\n\n")

  frame_files
}

# Run the complete animation pipeline (data -> frames -> video)
# @param data_path Path to RDS data file
# @param target_date Date to animate
# @param sensor_coords Sensor coordinates data frame
# @param map_extent Map extent list
# @param output_dir Output directory
# @param seconds_per_frame Duration each frame displays in video
# @param title_date Date string for frame titles
# @param cleanup_after Whether to delete frames after video creation
# @param parallel Use parallel processing for frame generation
# @param n_cores Number of cores for parallel processing (NULL = auto-detect)
# @return Path to generated video file
run_animation_pipeline <- function(data_path = "data/Eastie_UFP.rds",
                                    target_date = "2025-08-01",
                                    sensor_coords,
                                    map_extent,
                                    output_dir = "out",
                                    seconds_per_frame = 1,
                                    title_date = "August 1, 2025",
                                    cleanup_after = FALSE,
                                    parallel = TRUE,
                                    n_cores = NULL) {
  cat("\n")
  cat("============================================================\n")
  cat("       UFP Animation Pipeline\n")
  cat("============================================================\n")

  # Step 1: Process data
  processed_data <- process_data_pipeline(
    data_path = data_path,
    target_date = target_date,
    sensor_coords = sensor_coords
  )

  # Step 2: Generate frames
  frame_files <- generate_all_frames(
    processed_data = processed_data,
    sensor_coords = sensor_coords,
    map_extent = map_extent,
    output_dir = output_dir,
    title_date = title_date,
    parallel = parallel,
    n_cores = n_cores
  )

  # Step 3: Create video
  video_file <- file.path(output_dir, "animation.mp4")
  frame_rate <- seconds_to_framerate(seconds_per_frame)

  # Print duration info
  duration_info <- get_video_duration_info(length(frame_files), seconds_per_frame)
  cat("Video duration:", duration_info, "\n")

  create_video_from_frames(
    frames_dir = output_dir,
    output_file = video_file,
    frame_rate = frame_rate
  )

  # Optional cleanup
  if (cleanup_after) {
    cleanup_frames(output_dir)
  }

  cat("============================================================\n")
  cat("       Pipeline Complete!\n")
  cat("============================================================\n")
  cat("Video saved to:", video_file, "\n\n")

  video_file
}
