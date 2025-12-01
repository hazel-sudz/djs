#!/usr/bin/env python3
"""
Render UFP animations for all available days with enhanced visualization.

Features:
- Gaussian temporal smoothing
- Spatial pollution interpolation (heatmap)
- Wind-pollution correlation analysis
- Upwind/downwind sensor indicators
- Trend arrows

Usage:
    uv run python render_all_days.py
    uv run python render_all_days.py --days 2025-08-01 2025-08-02
"""

import argparse
import time
from pathlib import Path
import pandas as pd

from config import MAP_EXTENT, SENSOR_COORDS
from data_loader import load_rds_data
from map_tiles import create_base_map
from enhanced_processing import process_day_enhanced, get_pollution_stats
from enhanced_renderer import EnhancedMetalRenderer
from video_encoder import create_video


def get_available_dates(df: pd.DataFrame) -> list:
    """Get list of dates with data."""
    df['timestamp'] = pd.to_datetime(df['timestamp_local.x'], errors='coerce')
    df = df.dropna(subset=['timestamp'])
    dates = sorted(df['timestamp'].dt.date.unique())
    return [str(d) for d in dates]


def render_day(df: pd.DataFrame, date: str, base_map_path: str,
               output_dir: str, width: int, height: int,
               seconds_per_frame: float = 0.5) -> str:
    """Render video for a single day."""
    print(f"\n{'='*60}")
    print(f"  Processing {date}")
    print(f"{'='*60}")

    # Create day output directory
    day_output = Path(output_dir) / date
    day_output.mkdir(parents=True, exist_ok=True)

    # Process data with enhanced analysis
    print("Processing data with Gaussian smoothing...")
    frames = process_day_enhanced(
        df, date, SENSOR_COORDS, MAP_EXTENT,
        frame_interval_minutes=5.0,
        smoothing_sigma_minutes=10.0
    )

    if len(frames) == 0:
        print(f"  No valid frames for {date}, skipping")
        return None

    print(f"  Generated {len(frames)} frames")

    # Get pollution stats for consistent color scaling
    stats = get_pollution_stats(frames)
    print(f"  Pollution range: {stats['min']:.0f} - {stats['max']:.0f}")

    # Create renderer
    renderer = EnhancedMetalRenderer(
        width=width, height=height,
        map_extent=MAP_EXTENT,
        pollution_min=stats['min'],
        pollution_max=stats['max']
    )
    renderer.load_base_map(base_map_path)

    # Render frames
    renderer.render_all_frames(frames, str(day_output), num_workers=8)

    # Create video
    video_file = str(day_output / "animation.mp4")
    frame_rate = 1.0 / seconds_per_frame

    create_video(str(day_output), video_file, frame_rate=frame_rate, use_hevc=True)

    return video_file


def main():
    parser = argparse.ArgumentParser(description="Render UFP animations for all days")
    parser.add_argument("--data", default="../animation/data/Eastie_UFP.rds", help="Path to RDS data")
    parser.add_argument("--output", default="out_all_days", help="Output directory")
    parser.add_argument("--days", nargs="*", help="Specific days to render (YYYY-MM-DD)")
    parser.add_argument("--width", type=int, default=1800, help="Frame width")
    parser.add_argument("--height", type=int, default=1200, help="Frame height")
    parser.add_argument("--fps", type=float, default=0.5, help="Seconds per frame")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  UFP Animation - Multi-Day Enhanced Renderer")
    print("="*60)
    print("Features: Gaussian smoothing, pollution heatmap, wind correlation")
    print()

    total_start = time.time()

    # Load data
    print("Loading data...")
    df = load_rds_data(args.data)
    df['timestamp'] = pd.to_datetime(df['timestamp_local.x'], errors='coerce')

    # Get dates to process
    if args.days:
        dates = args.days
    else:
        dates = get_available_dates(df)

    print(f"Days to process: {len(dates)}")
    for d in dates:
        print(f"  - {d}")

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create base map (once)
    base_map_path = output_dir / "base_map.png"
    if not base_map_path.exists():
        print("\nCreating base map...")
        create_base_map(MAP_EXTENT, str(base_map_path), args.width, args.height, zoom=15)
    else:
        print(f"\nUsing existing base map: {base_map_path}")

    # Render each day
    videos = []
    for date in dates:
        video = render_day(
            df, date, str(base_map_path),
            str(output_dir), args.width, args.height,
            args.fps
        )
        if video:
            videos.append((date, video))

    # Summary
    total_elapsed = time.time() - total_start

    print("\n" + "="*60)
    print("  All Days Complete!")
    print("="*60)
    print(f"Total time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")
    print(f"\nVideos created:")
    for date, video in videos:
        print(f"  {date}: {video}")

    # Create index file
    index_file = output_dir / "index.txt"
    with open(index_file, 'w') as f:
        f.write("UFP Animation Videos\n")
        f.write("="*40 + "\n\n")
        for date, video in videos:
            f.write(f"{date}: {Path(video).name}\n")

    print(f"\nIndex file: {index_file}")


if __name__ == "__main__":
    main()
