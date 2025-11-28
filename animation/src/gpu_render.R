# =============================================================================
# GPU-Accelerated Rendering using Metal (M2)
# =============================================================================
# This module exports frame data to JSON and uses a Swift Metal renderer
# for hardware-accelerated PNG generation on Apple Silicon.

# Path to the compiled Swift renderer
GPU_RENDERER_PATH <- "gpu_renderer/.build/release/render-frames"

# Check if GPU renderer is available
gpu_renderer_available <- function() {
  file.exists(GPU_RENDERER_PATH)
}

# Build the GPU renderer if needed
build_gpu_renderer <- function() {
  cat("Building Metal GPU renderer...\n")

  # Navigate to gpu_renderer directory and build
  old_wd <- getwd()
  setwd("gpu_renderer")

  result <- system("swift build -c release 2>&1", intern = TRUE)
  build_success <- file.exists(".build/release/render-frames")

  setwd(old_wd)

  if (build_success) {
    cat("GPU renderer built successfully!\n")
  } else {
    cat("Failed to build GPU renderer:\n")
    cat(paste(result, collapse = "\n"), "\n")
  }

  build_success
}

# Pre-render the base map using R (one-time operation)
render_base_map <- function(map_extent, output_path = "out/base_map.png",
                            width = 1800, height = 1200) {
  cat("Pre-rendering base map...\n")

  # Create base map without any dynamic elements
  base_map <- ggplot() +
    annotation_map_tile(type = "osm", zoomin = 1) +
    coord_sf(
      xlim = c(map_extent$lon_min, map_extent$lon_max),
      ylim = c(map_extent$lat_min, map_extent$lat_max),
      crs = 4326
    ) +
    theme_void() +
    theme(
      panel.background = element_rect(fill = "white", color = NA),
      plot.background = element_rect(fill = "white", color = NA)
    )

  ggsave(output_path, plot = base_map, width = width/150, height = height/150,
         dpi = 150, bg = "white", device = ragg::agg_png)

  cat("Base map saved to:", output_path, "\n")
  output_path
}

# Export frame data to JSON for the GPU renderer
export_frames_to_json <- function(processed_data, sensor_coords, map_extent,
                                   pollution_stats, title_date = "August 1, 2025",
                                   width = 1800, height = 1200,
                                   base_map_path = NULL, output_dir = "out") {
  unique_times <- processed_data$unique_times
  animation_data <- processed_data$animation_data
  wind_summary <- processed_data$wind_summary

  cat("Exporting", length(unique_times), "frames to JSON...\n")

  # Calculate map center
  lon_center <- (map_extent$lon_min + map_extent$lon_max) / 2
  lat_center <- (map_extent$lat_min + map_extent$lat_max) / 2

  # Arrow scale (40% of smaller dimension)
  map_lat_range <- map_extent$lat_max - map_extent$lat_min
  map_lon_range <- map_extent$lon_max - map_extent$lon_min
  arrow_scale <- min(map_lat_range, map_lon_range) * 0.4

  frames <- lapply(seq_along(unique_times), function(i) {
    current_time <- unique_times[i]

    # Filter data for current time
    time_data <- animation_data %>% filter(time_group == current_time)
    wind_data <- wind_summary %>% filter(time_group == current_time)

    # Build sensor data
    sensors <- lapply(seq_len(nrow(time_data)), function(j) {
      row <- time_data[j, ]
      list(
        lon = row$lon,
        lat = row$lat,
        pollution = row$pollution,
        label = format_pollution_label(row$pollution)
      )
    })

    # Build wind data
    wind <- NULL
    if (nrow(wind_data) > 0 && !is.na(wind_data$avg_wind_u[1]) && !is.na(wind_data$avg_wind_v[1])) {
      wind_speed <- wind_data$avg_wind_speed[1]
      wind_u <- wind_data$avg_wind_u[1]
      wind_v <- wind_data$avg_wind_v[1]

      if (!is.na(wind_speed) && wind_speed > 0) {
        wind_magnitude <- sqrt(wind_u^2 + wind_v^2)
        if (wind_magnitude > 0) {
          arrow_length <- arrow_scale * min(wind_speed / 6.0, 1.0)
          end_lon <- lon_center + (wind_u / wind_magnitude) * arrow_length
          end_lat <- lat_center + (wind_v / wind_magnitude) * arrow_length

          wind <- list(
            centerLon = lon_center,
            centerLat = lat_center,
            endLon = end_lon,
            endLat = end_lat,
            speedLabel = format_wind_label(wind_speed)
          )
        }
      }
    }

    list(
      frameNumber = i,
      timeLabel = format(current_time, "%H:%M:%S"),
      titleDate = title_date,
      sensors = sensors,
      wind = wind
    )
  })

  # Build config
  config <- list(
    width = width,
    height = height,
    mapExtent = list(
      lonMin = map_extent$lon_min,
      lonMax = map_extent$lon_max,
      latMin = map_extent$lat_min,
      latMax = map_extent$lat_max
    ),
    pollutionMin = pollution_stats$min,
    pollutionMax = pollution_stats$max,
    baseMapPath = base_map_path,
    outputDir = output_dir,
    frames = frames
  )

  # Write JSON
  json_path <- file.path(output_dir, "render_config.json")
  jsonlite::write_json(config, json_path, auto_unbox = TRUE, pretty = FALSE)

  cat("Frame data exported to:", json_path, "\n")
  json_path
}

# Run the GPU renderer
run_gpu_renderer <- function(config_path) {
  cat("\n=== Metal GPU Frame Rendering ===\n")

  if (!gpu_renderer_available()) {
    cat("GPU renderer not found. Building...\n")
    if (!build_gpu_renderer()) {
      stop("Failed to build GPU renderer")
    }
  }

  # Run the renderer
  cmd <- sprintf("%s %s", GPU_RENDERER_PATH, shQuote(config_path))
  cat("Running:", cmd, "\n\n")

  start_time <- Sys.time()
  result <- system(cmd, intern = FALSE)
  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))

  if (result != 0) {
    stop("GPU renderer failed with exit code: ", result)
  }

  cat("\n=== GPU Rendering Complete ===\n")
  cat("Total time:", round(elapsed, 1), "seconds\n")

  invisible(result)
}

# Generate frames using Metal GPU acceleration
generate_frames_gpu <- function(processed_data, sensor_coords, map_extent,
                                 output_dir = "out", title_date = "August 1, 2025",
                                 width = 1800, height = 1200) {
  n_frames <- length(processed_data$unique_times)

  # Ensure output directory exists
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  cat("\n=== GPU-Accelerated Frame Generation ===\n")
  cat("Frames to generate:", n_frames, "\n")
  cat("Resolution:", width, "x", height, "\n")

  # Step 1: Pre-render the base map (one-time)
  base_map_path <- file.path(output_dir, "base_map.png")
  if (!file.exists(base_map_path)) {
    base_map_path <- render_base_map(map_extent, base_map_path, width, height)
  } else {
    cat("Using existing base map:", base_map_path, "\n")
  }

  # Step 2: Export frame data to JSON
  config_path <- export_frames_to_json(
    processed_data = processed_data,
    sensor_coords = sensor_coords,
    map_extent = map_extent,
    pollution_stats = processed_data$pollution_stats,
    title_date = title_date,
    width = width,
    height = height,
    base_map_path = normalizePath(base_map_path),
    output_dir = normalizePath(output_dir)
  )

  # Step 3: Run GPU renderer
  run_gpu_renderer(config_path)

  # Return list of frame files
  frame_files <- sprintf("%s/frame_%04d.png", output_dir, seq_len(n_frames))
  frame_files
}

# Create video using FFmpeg with VideoToolbox hardware acceleration (M2)
create_video_hardware_accelerated <- function(frames_dir = "out",
                                               output_file = "out/animation.mp4",
                                               frame_rate = 1,
                                               use_hevc = TRUE) {
  cat("\n=== Hardware-Accelerated Video Encoding ===\n")

  # Check if ffmpeg is available
  ffmpeg_check <- system("which ffmpeg", intern = TRUE, ignore.stderr = TRUE)
  if (length(ffmpeg_check) == 0) {
    stop("FFmpeg not found. Please install FFmpeg: brew install ffmpeg")
  }

  # Count frames
  frame_files <- list.files(frames_dir, pattern = "^frame_.*\\.png$", full.names = TRUE)
  cat("Found", length(frame_files), "frames\n")
  cat("Frame rate:", frame_rate, "fps\n")

  # Build FFmpeg command with VideoToolbox (Apple Silicon hardware acceleration)
  input_pattern <- file.path(frames_dir, "frame_%04d.png")

  if (use_hevc) {
    # HEVC with VideoToolbox - best quality and compression on M2
    encoder <- "hevc_videotoolbox"
    extra_opts <- "-tag:v hvc1"  # For better compatibility
  } else {
    # H.264 with VideoToolbox
    encoder <- "h264_videotoolbox"
    extra_opts <- ""
  }

  cmd <- sprintf(
    'ffmpeg -y -framerate %s -i "%s" -c:v %s -q:v 65 %s -pix_fmt yuv420p "%s"',
    frame_rate,
    input_pattern,
    encoder,
    extra_opts,
    output_file
  )

  cat("Encoder:", encoder, "(Metal GPU accelerated)\n")
  cat("Running FFmpeg...\n")

  start_time <- Sys.time()
  result <- system(cmd, ignore.stdout = TRUE, ignore.stderr = TRUE)
  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))

  if (result != 0) {
    # Fallback to software encoding if hardware encoding fails
    cat("Hardware encoding failed, falling back to software encoding...\n")
    cmd <- sprintf(
      'ffmpeg -y -framerate %s -i "%s" -c:v libx264 -crf 18 -pix_fmt yuv420p "%s"',
      frame_rate,
      input_pattern,
      output_file
    )
    result <- system(cmd, ignore.stdout = TRUE, ignore.stderr = TRUE)
  }

  if (result == 0) {
    file_size <- file.info(output_file)$size / 1024 / 1024
    cat("Video created:", output_file, "\n")
    cat("File size:", round(file_size, 2), "MB\n")
    cat("Encoding time:", round(elapsed, 1), "seconds\n")
  } else {
    stop("Video encoding failed")
  }

  cat("=== Video Encoding Complete ===\n\n")
  output_file
}

# Main GPU-accelerated animation pipeline
run_animation_pipeline_gpu <- function(data_path = "data/Eastie_UFP.rds",
                                        target_date = "2025-08-01",
                                        sensor_coords,
                                        map_extent,
                                        output_dir = "out",
                                        seconds_per_frame = 1,
                                        title_date = "August 1, 2025",
                                        cleanup_after = FALSE,
                                        width = 1800,
                                        height = 1200) {
  cat("\n")
  cat("============================================================\n")
  cat("       UFP Animation Pipeline (Metal GPU Accelerated)\n")
  cat("============================================================\n")
  cat("Using Apple M2 Metal GPU for rendering\n\n")

  # Step 1: Process data
  processed_data <- process_data_pipeline(
    data_path = data_path,
    target_date = target_date,
    sensor_coords = sensor_coords
  )

  # Step 2: Generate frames using GPU
  frame_files <- generate_frames_gpu(
    processed_data = processed_data,
    sensor_coords = sensor_coords,
    map_extent = map_extent,
    output_dir = output_dir,
    title_date = title_date,
    width = width,
    height = height
  )

  # Step 3: Create video with hardware-accelerated encoding
  video_file <- file.path(output_dir, "animation.mp4")
  frame_rate <- 1 / seconds_per_frame

  # Print duration info
  duration_info <- get_video_duration_info(length(frame_files), seconds_per_frame)
  cat("Video duration:", duration_info, "\n")

  create_video_hardware_accelerated(
    frames_dir = output_dir,
    output_file = video_file,
    frame_rate = frame_rate,
    use_hevc = TRUE
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
