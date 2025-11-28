# =============================================================================
# UFP Animation - Main Entry Point
# =============================================================================
# Generates animated visualization of Ultrafine Particle (UFP) sensor data.
#
# Usage: Rscript main.R
#
# This script will:
#   1. Load and process UFP sensor data
#   2. Generate animation frames with map backgrounds (in parallel)
#   3. Combine frames into an MP4 video
#
# Output: out/animation.mp4
# =============================================================================

# Source all modules (order matters due to dependencies)
source("src/setup.R")           # Package management
source("src/constants.R")       # Sensor coordinates and map extent
source("src/maps.R")            # Base map functions
source("src/plot_elements.R")   # Pollution circles, labels, and wind arrows
source("src/data_processing.R") # Data loading and processing
source("src/video.R")           # Video generation
source("src/parallel.R")        # Parallel processing functions
source("src/animate.R")         # Animation frame generation

# =============================================================================
# Configuration
# =============================================================================
config <- list(
  data_path = "data/Eastie_UFP.rds",
  target_date = "2025-08-01",
  title_date = "August 1, 2025",
  output_dir = "out",
  seconds_per_frame = 1,    # 1 second per frame
  cleanup_frames = FALSE,   # Set to TRUE to delete frames after video creation
  parallel = TRUE,          # Use parallel processing for faster frame generation
  n_cores = NULL            # NULL = auto-detect, or set specific number
)

# =============================================================================
# Run Pipeline
# =============================================================================
video_path <- run_animation_pipeline(
  data_path = config$data_path,
  target_date = config$target_date,
  sensor_coords = sensor_coords,
  map_extent = map_extent,
  output_dir = config$output_dir,
  seconds_per_frame = config$seconds_per_frame,
  title_date = config$title_date,
  cleanup_after = config$cleanup_frames,
  parallel = config$parallel,
  n_cores = config$n_cores
)
