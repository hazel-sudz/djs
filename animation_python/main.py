#!/usr/bin/env python3
"""
UFP Animation Pipeline - Python with M2 Metal GPU Acceleration

Usage:
    python main.py                    # Run with default settings
    python main.py --data path.rds    # Specify data file
    python main.py --date 2025-08-01  # Specify date to animate

This pipeline:
    1. Loads UFP sensor data from RDS file
    2. Fetches and caches OSM map tiles
    3. Renders frames using Core Graphics (Metal GPU on M2)
    4. Encodes video using VideoToolbox (hardware H.265)

Performance: ~100x faster than R/ggplot2 on Apple Silicon
"""

import argparse
import time
from pathlib import Path

from config import Config, MAP_EXTENT, SENSOR_COORDS
from data_loader import load_rds_data, process_data
from map_tiles import create_base_map
from gpu_renderer import MetalRenderer, FrameData
from video_encoder import create_video, cleanup_frames


def format_pollution_label(value: float) -> str:
    """Format pollution value for display."""
    if value >= 1000:
        return f"{value/1000:.1f}K p/cm³"
    return f"{value:.0f} p/cm³"


def format_wind_label(speed: float) -> str:
    """Format wind speed for display."""
    return f"{speed:.1f} m/s"


def prepare_frame_data(processed_data, map_extent, title_date: str) -> list[FrameData]:
    """Convert processed data to FrameData objects for rendering."""
    frames = []

    animation_data = processed_data.animation_data
    wind_summary = processed_data.wind_summary
    unique_times = processed_data.unique_times

    # Calculate wind arrow parameters
    lon_center = map_extent.lon_center
    lat_center = map_extent.lat_center
    lat_range = map_extent.lat_max - map_extent.lat_min
    lon_range = map_extent.lon_max - map_extent.lon_min
    arrow_scale = min(lat_range, lon_range) * 0.4

    for i, current_time in enumerate(unique_times):
        # Filter data for current time
        time_data = animation_data[animation_data['time_group'] == current_time]
        wind_data = wind_summary[wind_summary['time_group'] == current_time]

        # Build sensor data
        sensors = []
        for _, row in time_data.iterrows():
            sensors.append((
                row['lon'],
                row['lat'],
                row['pollution'],
                format_pollution_label(row['pollution'])
            ))

        # Build wind data
        wind = None
        if len(wind_data) > 0:
            wind_row = wind_data.iloc[0]
            wind_u = wind_row.get('avg_wind_u', 0)
            wind_v = wind_row.get('avg_wind_v', 0)
            wind_speed = wind_row.get('avg_wind_speed', 0)

            if wind_speed and wind_speed > 0:
                import math
                wind_magnitude = math.sqrt(wind_u**2 + wind_v**2)
                if wind_magnitude > 0:
                    arrow_length = arrow_scale * min(wind_speed / 6.0, 1.0)
                    end_lon = lon_center + (wind_u / wind_magnitude) * arrow_length
                    end_lat = lat_center + (wind_v / wind_magnitude) * arrow_length

                    wind = {
                        'center_lon': lon_center,
                        'center_lat': lat_center,
                        'end_lon': end_lon,
                        'end_lat': end_lat,
                        'speed_label': format_wind_label(wind_speed)
                    }

        # Format time label
        time_label = current_time.strftime("%H:%M:%S")

        frames.append(FrameData(
            frame_number=i + 1,
            time_label=time_label,
            title_date=title_date,
            sensors=sensors,
            wind=wind
        ))

    return frames


def run_pipeline(config: Config):
    """Run the complete animation pipeline."""
    print("\n" + "=" * 60)
    print("       UFP Animation Pipeline (Python + Metal GPU)")
    print("=" * 60)
    print("Using Apple M2 Metal GPU for rendering")
    print()

    total_start = time.time()

    # Step 1: Load and process data
    print("=== Data Processing ===")
    df = load_rds_data(config.data_path)
    processed_data = process_data(df, config.target_date, SENSOR_COORDS)
    print()

    # Step 2: Create/load base map
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_map_path = output_dir / "base_map.png"
    if not base_map_path.exists():
        create_base_map(
            MAP_EXTENT,
            str(base_map_path),
            config.width,
            config.height,
            zoom=15
        )
    else:
        print(f"Using cached base map: {base_map_path}")
    print()

    # Step 3: Prepare frame data
    print("=== Preparing Frame Data ===")
    frames = prepare_frame_data(processed_data, MAP_EXTENT, config.title_date)
    print(f"  Frames prepared: {len(frames)}")
    print()

    # Step 4: Render frames with GPU
    print("=== GPU Frame Rendering ===")
    renderer = MetalRenderer(
        width=config.width,
        height=config.height,
        map_extent=MAP_EXTENT,
        pollution_min=processed_data.pollution_stats['min'],
        pollution_max=processed_data.pollution_stats['max'],
    )
    renderer.load_base_map(str(base_map_path))

    render_start = time.time()
    renderer.render_all_frames(frames, config.output_dir, num_workers=8)
    render_elapsed = time.time() - render_start
    print()

    # Step 5: Create video
    video_file = str(output_dir / "animation.mp4")
    frame_rate = 1.0 / config.seconds_per_frame

    n_frames = len(frames)
    duration_secs = n_frames * config.seconds_per_frame
    duration_mins = int(duration_secs // 60)
    duration_remainder = duration_secs % 60
    print(f"Video duration: {n_frames} frames x {config.seconds_per_frame} sec = {duration_mins} min {duration_remainder:.0f} sec")

    create_video(
        config.output_dir,
        video_file,
        frame_rate=frame_rate,
        use_hevc=True
    )

    # Optional cleanup
    if config.cleanup_frames:
        cleanup_frames(config.output_dir)

    total_elapsed = time.time() - total_start

    print("=" * 60)
    print("       Pipeline Complete!")
    print("=" * 60)
    print(f"Video saved to: {video_file}")
    print(f"Total pipeline time: {total_elapsed:.1f} seconds")
    print(f"  - Frame rendering: {render_elapsed:.1f} seconds")
    print()

    return video_file


def main():
    parser = argparse.ArgumentParser(
        description="UFP Animation Pipeline with M2 Metal GPU acceleration"
    )
    parser.add_argument(
        "--data",
        default="../animation/data/Eastie_UFP.rds",
        help="Path to RDS data file"
    )
    parser.add_argument(
        "--date",
        default="2025-08-01",
        help="Target date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--title-date",
        default="August 1, 2025",
        help="Date string for display in title"
    )
    parser.add_argument(
        "--output",
        default="out",
        help="Output directory"
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=0.5,
        help="Seconds per frame (default: 0.5 for 2x speed)"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1800,
        help="Frame width (default: 1800)"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=1200,
        help="Frame height (default: 1200)"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete frame files after video creation"
    )

    args = parser.parse_args()

    config = Config(
        data_path=args.data,
        target_date=args.date,
        title_date=args.title_date,
        output_dir=args.output,
        seconds_per_frame=args.fps,
        width=args.width,
        height=args.height,
        cleanup_frames=args.cleanup,
    )

    run_pipeline(config)


if __name__ == "__main__":
    main()
