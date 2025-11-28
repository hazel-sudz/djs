# =============================================================================
# Video Generation Functions
# =============================================================================
# Functions for combining animation frames into video files using the av package.

# Create video from PNG frames using av package
# @param frames_dir Directory containing the frame PNG files
# @param output_file Output video file path (e.g., "out/animation.mp4")
# @param frame_rate Frames per second (lower = slower animation)
# @param frame_pattern Glob pattern for frame files (default: "frame_*.png")
# @return Path to the created video file
create_video_from_frames <- function(frames_dir = "out",
                                      output_file = "out/animation.mp4",
                                      frame_rate = 0.5,
                                      frame_pattern = "frame_*.png") {
  # Get list of frame files
  frame_files <- list.files(
    path = frames_dir,
    pattern = glob2rx(frame_pattern),
    full.names = TRUE
  )

  if (length(frame_files) == 0) {
    stop(paste("No frame files found in", frames_dir, "matching pattern", frame_pattern))
  }

  # Sort files to ensure correct order
  frame_files <- sort(frame_files)

  cat("\n=== Video Generation ===\n")
  cat("Found", length(frame_files), "frames\n")
  cat("Frame rate:", frame_rate, "fps (", 1/frame_rate, "seconds per frame)\n")
  cat("Output file:", output_file, "\n")

  # Create video using av package
  av::av_encode_video(
    input = frame_files,
    output = output_file,
    framerate = frame_rate,
    verbose = FALSE
  )

  cat("Video created successfully:", output_file, "\n")
  cat("=== Video Generation Complete ===\n\n")

  output_file
}

# Calculate frame rate from desired seconds per frame
# @param seconds_per_frame How many seconds each frame should display
# @return Frame rate (fps) value for av_encode_video
seconds_to_framerate <- function(seconds_per_frame) {
  1 / seconds_per_frame
}

# Clean up frame files after video generation (optional)
# @param frames_dir Directory containing frame files
# @param frame_pattern Pattern for frame files to delete
# @param confirm Whether to prompt for confirmation (not used in non-interactive)
# @return Number of files deleted
cleanup_frames <- function(frames_dir = "out", frame_pattern = "frame_*.png", confirm = FALSE) {
  frame_files <- list.files(
    path = frames_dir,
    pattern = glob2rx(frame_pattern),
    full.names = TRUE
  )

  if (length(frame_files) == 0) {
    cat("No frame files to clean up\n")
    return(0)
  }

  cat("Removing", length(frame_files), "frame files...\n")
  file.remove(frame_files)
  cat("Cleanup complete\n")

  length(frame_files)
}

# Get video duration info
# @param n_frames Number of frames
# @param seconds_per_frame Seconds each frame displays
# @return String describing video duration
get_video_duration_info <- function(n_frames, seconds_per_frame) {
  total_seconds <- n_frames * seconds_per_frame
  minutes <- floor(total_seconds / 60)
  seconds <- total_seconds %% 60

  if (minutes > 0) {
    sprintf("%d frames x %.1f sec = %d min %.0f sec total",
            n_frames, seconds_per_frame, minutes, seconds)
  } else {
    sprintf("%d frames x %.1f sec = %.0f sec total",
            n_frames, seconds_per_frame, total_seconds)
  }
}
