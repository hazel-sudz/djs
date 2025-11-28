#!/usr/bin/env python3
"""
Render UFP animations with improved wind visualization and combined multi-day video.

Key improvements:
1. Wind streamlines drawn directly on map (not in corner)
2. Pollution plumes extending downwind from each sensor
3. Transport arrows between sensors
4. Combined video spanning all days

Usage:
    uv run python render_combined.py
    uv run python render_combined.py --days 2025-08-01 2025-08-02
"""

import argparse
import time
from pathlib import Path
import pandas as pd
import subprocess

from config import MAP_EXTENT, SENSOR_COORDS
from data_loader import load_rds_data
from map_tiles import create_base_map
from enhanced_processing import process_day_enhanced, get_pollution_stats
from improved_renderer import ImprovedRenderer
from video_encoder import create_video


def get_available_dates(df: pd.DataFrame) -> list:
    """Get list of dates with data."""
    df['timestamp'] = pd.to_datetime(df['timestamp_local.x'], errors='coerce')
    df = df.dropna(subset=['timestamp'])
    dates = sorted(df['timestamp'].dt.date.unique())
    return [str(d) for d in dates]


def get_global_pollution_stats(df: pd.DataFrame, dates: list, sensor_coords: list, map_extent) -> dict:
    """Get pollution stats across ALL days for consistent color scaling."""
    all_pollution = []

    for date in dates:
        frames = process_day_enhanced(
            df, date, sensor_coords, map_extent,
            frame_interval_minutes=5.0,
            smoothing_sigma_minutes=10.0
        )
        for frame in frames:
            for sensor in frame.sensors:
                all_pollution.append(sensor[2])

    if len(all_pollution) == 0:
        return {'min': 0, 'max': 100000}

    return {
        'min': min(all_pollution),
        'max': max(all_pollution)
    }


def render_frames_for_day(df: pd.DataFrame, date: str, renderer: ImprovedRenderer,
                          output_dir: Path, start_frame: int) -> tuple:
    """
    Render frames for a single day.

    Returns:
        (next_frame_number, num_frames_rendered)
    """
    print(f"\n  Processing {date}...")

    # Process data
    frames = process_day_enhanced(
        df, date, SENSOR_COORDS, MAP_EXTENT,
        frame_interval_minutes=5.0,
        smoothing_sigma_minutes=10.0
    )

    if len(frames) == 0:
        print(f"    No valid frames, skipping")
        return start_frame, 0

    print(f"    {len(frames)} frames")

    # Render frames
    next_frame = renderer.render_all_frames(frames, str(output_dir), num_workers=8, start_frame=start_frame)

    return next_frame, len(frames)


def create_combined_video(frame_dir: str, output_file: str, frame_rate: float = 2.0):
    """Create video from all frames in directory."""
    print(f"\nCreating combined video: {output_file}")

    # Use ffmpeg with hardware encoding
    cmd = [
        'ffmpeg', '-y',
        '-framerate', str(frame_rate),
        '-i', f'{frame_dir}/frame_%05d.png',
        '-c:v', 'hevc_videotoolbox',  # M2 hardware encoder
        '-tag:v', 'hvc1',
        '-q:v', '65',
        '-pix_fmt', 'yuv420p',
        output_file
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Warning: HEVC encoding failed, trying H.264")
        cmd[5] = 'h264_videotoolbox'
        cmd.pop(6)  # Remove -tag:v
        cmd.pop(6)  # Remove hvc1
        subprocess.run(cmd)

    print(f"  Done: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Render UFP animations with improved wind visualization")
    parser.add_argument("--data", default="../animation/data/Eastie_UFP.rds", help="Path to RDS data")
    parser.add_argument("--output", default="out_improved", help="Output directory")
    parser.add_argument("--days", nargs="*", help="Specific days to render (YYYY-MM-DD)")
    parser.add_argument("--width", type=int, default=1800, help="Frame width")
    parser.add_argument("--height", type=int, default=1200, help="Frame height")
    parser.add_argument("--fps", type=float, default=0.5, help="Seconds per frame")
    parser.add_argument("--no-combined", action="store_true", help="Skip combined video")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  UFP Animation - Improved Wind Visualization")
    print("="*60)
    print("Features:")
    print("  • Wind streamlines on map")
    print("  • Pollution plumes extending downwind")
    print("  • Transport arrows between sensors")
    print("  • Combined multi-day video")
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

    print(f"\nDays to process: {len(dates)}")
    for d in dates:
        print(f"  • {d}")

    # Create output directories
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    combined_frames_dir = output_dir / "combined_frames"
    combined_frames_dir.mkdir(parents=True, exist_ok=True)

    # Create base map
    base_map_path = output_dir / "base_map.png"
    if not base_map_path.exists():
        print("\nCreating base map...")
        create_base_map(MAP_EXTENT, str(base_map_path), args.width, args.height, zoom=15)
    else:
        print(f"\nUsing existing base map: {base_map_path}")

    # Get global pollution stats for consistent color scaling
    print("\nCalculating global pollution range...")
    stats = get_global_pollution_stats(df, dates, SENSOR_COORDS, MAP_EXTENT)
    print(f"  Range: {stats['min']:.0f} - {stats['max']:.0f}")

    # Create renderer with global stats
    renderer = ImprovedRenderer(
        width=args.width, height=args.height,
        map_extent=MAP_EXTENT,
        pollution_min=stats['min'],
        pollution_max=stats['max']
    )
    renderer.load_base_map(str(base_map_path))

    # Render all days with sequential frame numbering
    print("\n" + "="*60)
    print("  Rendering Frames")
    print("="*60)

    frame_count = 1
    day_info = []

    for date in dates:
        start_frame = frame_count
        next_frame, num_frames = render_frames_for_day(
            df, date, renderer,
            combined_frames_dir, frame_count
        )

        if num_frames > 0:
            day_info.append({
                'date': date,
                'start_frame': start_frame,
                'end_frame': next_frame - 1,
                'num_frames': num_frames
            })
            frame_count = next_frame

    total_frames = frame_count - 1
    print(f"\n  Total frames rendered: {total_frames}")

    # Create combined video
    if not args.no_combined and total_frames > 0:
        print("\n" + "="*60)
        print("  Creating Combined Video")
        print("="*60)

        combined_video = str(output_dir / "combined_animation.mp4")
        frame_rate = 1.0 / args.fps
        create_combined_video(str(combined_frames_dir), combined_video, frame_rate)

    # Also create per-day videos (by creating concat file from frames)
    print("\n" + "="*60)
    print("  Creating Per-Day Videos")
    print("="*60)

    frame_rate = 1.0 / args.fps
    for info in day_info:
        date = info['date']
        day_video = str(output_dir / f"{date}_animation.mp4")

        # Create symlinks or copy frames for this day
        day_frames_dir = output_dir / f"frames_{date}"
        day_frames_dir.mkdir(parents=True, exist_ok=True)

        # Create symlinks to relevant frames
        for i, frame_num in enumerate(range(info['start_frame'], info['end_frame'] + 1)):
            src = combined_frames_dir / f"frame_{frame_num:05d}.png"
            dst = day_frames_dir / f"frame_{i+1:05d}.png"
            if dst.exists():
                dst.unlink()
            dst.symlink_to(src.absolute())

        # Create video
        print(f"\n  {date}...")
        create_combined_video(str(day_frames_dir), day_video, frame_rate)

    # Summary
    total_elapsed = time.time() - total_start

    print("\n" + "="*60)
    print("  Complete!")
    print("="*60)
    print(f"\nTotal time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"Total frames: {total_frames}")
    print(f"Performance: {total_frames/total_elapsed:.1f} fps")

    print(f"\nOutput files:")
    print(f"  Combined video: {output_dir / 'combined_animation.mp4'}")
    print(f"\n  Per-day videos:")
    for info in day_info:
        date = info['date']
        print(f"    {date}: {output_dir / f'{date}_animation.mp4'}")

    # Create summary file
    summary_file = output_dir / "summary.txt"
    with open(summary_file, 'w') as f:
        f.write("UFP Animation - Improved Wind Visualization\n")
        f.write("="*50 + "\n\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total frames: {total_frames}\n")
        f.write(f"Render time: {total_elapsed:.1f}s\n\n")
        f.write("Features:\n")
        f.write("  - Wind streamlines drawn on map\n")
        f.write("  - Pollution plumes extending downwind\n")
        f.write("  - Transport arrows between sensors\n")
        f.write("  - Consistent color scaling across all days\n\n")
        f.write("Files:\n")
        f.write(f"  combined_animation.mp4 - All {len(dates)} days in one video\n\n")
        for info in day_info:
            f.write(f"  {info['date']}_animation.mp4 - Frames {info['start_frame']}-{info['end_frame']} ({info['num_frames']} frames)\n")

    print(f"\nSummary: {summary_file}")


if __name__ == "__main__":
    main()
