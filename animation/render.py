#!/usr/bin/env python3
"""
Render UFP animation - all days in one video.

Features:
- Pollution circles (size + color)
- Wind direction arrows from each sensor
- Single combined video for all days

Usage:
    uv run python render.py
    uv run python render.py --days 2025-08-01 2025-08-02
"""

import argparse
import time
from pathlib import Path
import subprocess
import pandas as pd

from config import MAP_EXTENT, SENSOR_COORDS
from data_loader import load_rds_data
from map_tiles import create_base_map
from processing import process_day, get_pollution_stats
from renderer import Renderer


def get_available_dates(df: pd.DataFrame) -> list:
    """Get list of dates with data."""
    df['timestamp'] = pd.to_datetime(df['timestamp_local.x'], errors='coerce')
    df = df.dropna(subset=['timestamp'])
    dates = sorted(df['timestamp'].dt.date.unique())
    return [str(d) for d in dates]


def get_global_pollution_stats(df: pd.DataFrame, dates: list, sensor_coords: list) -> dict:
    """Get pollution stats across ALL days for consistent color scaling."""
    all_pollution = []

    for date in dates:
        frames = process_day(df, date, sensor_coords)
        for frame in frames:
            for sensor in frame.sensors:
                all_pollution.append(sensor[2])

    if len(all_pollution) == 0:
        return {'min': 0, 'max': 100000}

    return {
        'min': min(all_pollution),
        'max': max(all_pollution)
    }


def create_video(frame_dir: str, output_file: str, frame_rate: float = 2.0):
    """Create video from frames using hardware encoding."""
    print(f"\nCreating video: {output_file}")

    cmd = [
        'ffmpeg', '-y',
        '-framerate', str(frame_rate),
        '-i', f'{frame_dir}/frame_%05d.png',
        '-c:v', 'hevc_videotoolbox',
        '-tag:v', 'hvc1',
        '-q:v', '65',
        '-pix_fmt', 'yuv420p',
        output_file
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  HEVC failed, trying H.264...")
        cmd = [
            'ffmpeg', '-y',
            '-framerate', str(frame_rate),
            '-i', f'{frame_dir}/frame_%05d.png',
            '-c:v', 'h264_videotoolbox',
            '-q:v', '65',
            '-pix_fmt', 'yuv420p',
            output_file
        ]
        subprocess.run(cmd, capture_output=True)

    # Get file size
    size_mb = Path(output_file).stat().st_size / (1024 * 1024)
    print(f"  Done: {output_file} ({size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Render UFP animation")
    parser.add_argument("--data", default="data/Eastie_UFP.rds", help="Path to RDS data")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--days", nargs="*", help="Specific days to render (YYYY-MM-DD)")
    parser.add_argument("--width", type=int, default=1800, help="Frame width")
    parser.add_argument("--height", type=int, default=1200, help="Frame height")
    parser.add_argument("--fps", type=float, default=2.0, help="Frames per second")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  UFP Animation Renderer")
    print("="*60)
    print("Features:")
    print("  • Pollution circles (size + color)")
    print("  • Wind arrows from each sensor")
    print("  • Single combined video")
    print()

    total_start = time.time()

    # Load data
    print("Loading data...")
    df = load_rds_data(args.data)
    df['timestamp'] = pd.to_datetime(df['timestamp_local.x'], errors='coerce')

    # Get dates
    if args.days:
        dates = args.days
    else:
        dates = get_available_dates(df)

    print(f"\nDays to process: {len(dates)}")
    for d in dates:
        print(f"  • {d}")

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # Create base map
    base_map_path = output_dir / "base_map.png"
    if not base_map_path.exists():
        print("\nCreating base map...")
        create_base_map(MAP_EXTENT, str(base_map_path), args.width, args.height, zoom=15)
    else:
        print(f"\nUsing existing base map: {base_map_path}")

    # Get global pollution stats
    print("\nCalculating global pollution range...")
    stats = get_global_pollution_stats(df, dates, SENSOR_COORDS)
    print(f"  Range: {stats['min']:.0f} - {stats['max']:.0f}")

    # Create renderer
    renderer = Renderer(
        width=args.width, height=args.height,
        map_extent=MAP_EXTENT,
        pollution_min=stats['min'],
        pollution_max=stats['max']
    )
    renderer.load_base_map(str(base_map_path))

    # Render all days
    print("\n" + "="*60)
    print("  Rendering Frames")
    print("="*60)

    frame_count = 1
    day_stats = []

    for date in dates:
        print(f"\n  {date}...")

        frames = process_day(df, date, SENSOR_COORDS)

        if len(frames) == 0:
            print(f"    No frames, skipping")
            continue

        start_frame = frame_count
        frame_count = renderer.render_all_frames(frames, str(frames_dir), num_workers=8, start_frame=frame_count)

        day_stats.append({
            'date': date,
            'start': start_frame,
            'end': frame_count - 1,
            'count': len(frames)
        })

    total_frames = frame_count - 1
    print(f"\n  Total frames: {total_frames}")

    # Create combined video
    print("\n" + "="*60)
    print("  Creating Video")
    print("="*60)

    video_file = str(output_dir / "animation.mp4")
    create_video(str(frames_dir), video_file, frame_rate=args.fps)

    # Summary
    elapsed = time.time() - total_start

    print("\n" + "="*60)
    print("  Complete!")
    print("="*60)
    print(f"\nTotal time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"Total frames: {total_frames}")
    print(f"Performance: {total_frames/elapsed:.1f} fps")
    print(f"\nOutput: {video_file}")

    # Day breakdown
    print("\nDays included:")
    for stat in day_stats:
        print(f"  {stat['date']}: {stat['count']} frames")


if __name__ == "__main__":
    main()
