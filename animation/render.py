#!/usr/bin/env python3
"""
Multi-site air quality animation renderer.

Supports multiple monitoring sites (East Boston, ECAGP, etc.) and
multiple pollution types per site (UFP, PM1, PM2.5, PM10).

Usage:
    # Render Eastie UFP (default)
    uv run python render.py

    # Render specific site
    uv run python render.py --site eastie
    uv run python render.py --site ecagp

    # Render specific pollution type
    uv run python render.py --site ecagp --pollution pm25

    # Render all pollution types for a site
    uv run python render.py --site ecagp --all

    # Render specific days
    uv run python render.py --days 2025-08-01 2025-08-02

    # Generate weekly videos (recommended for large datasets)
    uv run python render.py --site ecagp --all --weekly
"""

import argparse
import time
from pathlib import Path
import subprocess
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

from site_config import get_site_config, list_available_sites, SiteConfig, PollutionType
from data_loader import load_rds_data
from map_tiles import create_base_map
from processing import process_day, get_pollution_stats
from renderer import Renderer


def get_available_dates(df: pd.DataFrame, site_config: SiteConfig) -> list:
    """Get list of dates with data."""
    timestamp_col = site_config.column_mapping.timestamp
    if timestamp_col not in df.columns:
        # Fallback search
        for col in ['timestamp_local.x', 'timestamp_local.y', 'timestamp_local', 'timestamp', 'valid']:
            if col in df.columns:
                timestamp_col = col
                break
        else:
            raise ValueError(f"Could not find timestamp column")

    df['timestamp'] = pd.to_datetime(df[timestamp_col], errors='coerce')
    df = df.dropna(subset=['timestamp'])
    dates = sorted(df['timestamp'].dt.date.unique())
    return [str(d) for d in dates]


def group_dates_by_week(dates: list) -> dict:
    """Group dates by week (Monday start).

    Returns:
        Dictionary mapping week_start_date (str) to list of dates in that week
    """
    weeks = defaultdict(list)
    for date_str in dates:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        # Get Monday of the week
        week_start = date - timedelta(days=date.weekday())
        week_label = week_start.strftime("%Y-%m-%d")
        weeks[week_label].append(date_str)

    # Sort weeks and dates within each week
    return {k: sorted(v) for k, v in sorted(weeks.items())}


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
    if Path(output_file).exists():
        size_mb = Path(output_file).stat().st_size / (1024 * 1024)
        print(f"  Done: {output_file} ({size_mb:.1f} MB)")
    else:
        print(f"  Warning: Video file not created")


def render_animation(site_config: SiteConfig, pollution_type: PollutionType,
                     df: pd.DataFrame, dates: list, args, video_output_dir: Path = None) -> dict:
    """Render animation for a specific site and pollution type.

    Args:
        video_output_dir: Optional override for where to save the video

    Returns:
        Dictionary with rendering statistics
    """
    print(f"\n{'='*60}")
    print(f"  {site_config.display_name} - {pollution_type.display_name}")
    print(f"{'='*60}")

    # Create output directories
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use pollution-type-specific frames directory
    frames_dir = output_dir / f"frames_{site_config.name}_{pollution_type.name}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # Clear old frames
    for old_frame in frames_dir.glob("frame_*.png"):
        old_frame.unlink()

    # Create base map (shared per site)
    base_map_path = output_dir / f"{site_config.name}_base_map.png"
    map_extent = site_config.get_map_extent()

    if not base_map_path.exists():
        print("\nCreating base map...")
        create_base_map(map_extent, str(base_map_path), args.width, args.height, zoom=15)
    else:
        print(f"\nUsing existing base map: {base_map_path}")

    # Create renderer
    renderer = Renderer(
        width=args.width,
        height=args.height,
        site_config=site_config,
        pollution_type=pollution_type
    )
    renderer.load_base_map(str(base_map_path))

    # Render all days
    print("\nRendering frames...")
    frame_count = 1
    day_stats = []

    for date in dates:
        print(f"\n  {date}...")

        frames = process_day(df, date, site_config, pollution_type)

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

    if total_frames == 0:
        print("  No frames rendered")
        return {'total_frames': 0, 'video_file': None, 'day_stats': []}

    print(f"\n  Total frames: {total_frames}")

    # Create video - use override dir if provided
    if video_output_dir:
        video_output_dir.mkdir(parents=True, exist_ok=True)
        video_file = str(video_output_dir / site_config.get_video_filename(pollution_type))
    else:
        video_file = str(output_dir / site_config.get_video_filename(pollution_type))

    create_video(str(frames_dir), video_file, frame_rate=args.fps)

    return {
        'total_frames': total_frames,
        'video_file': video_file,
        'day_stats': day_stats
    }


def render_weekly(site_config: SiteConfig, pollution_types: list, df: pd.DataFrame,
                  dates: list, args) -> list:
    """Render weekly videos for a site.

    Output structure:
        output/videos/{site}/week_{YYYY-MM-DD}/{site}_{pollution}.mp4

    Returns:
        List of all results
    """
    weeks = group_dates_by_week(dates)
    total_weeks = len(weeks)

    print(f"\n{'='*60}")
    print(f"  Weekly Video Generation")
    print(f"{'='*60}")
    print(f"Site: {site_config.display_name}")
    print(f"Total weeks: {total_weeks}")
    print(f"Pollution types: {', '.join(pt.name for pt in pollution_types)}")
    print()

    all_results = []
    videos_base = Path(args.output) / "videos" / site_config.name

    for week_idx, (week_start, week_dates) in enumerate(weeks.items(), 1):
        print(f"\n{'#'*60}")
        print(f"  Week {week_idx}/{total_weeks}: {week_start}")
        print(f"  Days: {len(week_dates)} ({week_dates[0]} to {week_dates[-1]})")
        print(f"{'#'*60}")

        # Create week output directory
        week_dir = videos_base / f"week_{week_start}"

        for pollution_type in pollution_types:
            # Check if video already exists
            video_path = week_dir / site_config.get_video_filename(pollution_type)
            if video_path.exists():
                print(f"\n  Skipping {pollution_type.name} - video already exists: {video_path}")
                all_results.append({
                    'week': week_start,
                    'pollution_type': pollution_type,
                    'total_frames': 0,
                    'video_file': str(video_path),
                    'skipped': True
                })
                continue

            result = render_animation(
                site_config, pollution_type, df, week_dates, args,
                video_output_dir=week_dir
            )
            result['week'] = week_start
            result['pollution_type'] = pollution_type
            result['skipped'] = False
            all_results.append(result)

    return all_results


def main():
    parser = argparse.ArgumentParser(description="Multi-site air quality animation renderer")
    parser.add_argument("--site", default="eastie",
                        help=f"Site to render. Available: {', '.join(list_available_sites())}")
    parser.add_argument("--pollution", default=None,
                        help="Specific pollution type to render (e.g., ufp, pm1, pm25, pm10)")
    parser.add_argument("--all", action="store_true",
                        help="Render all pollution types for the site")
    parser.add_argument("--weekly", action="store_true",
                        help="Generate weekly videos instead of one large video")
    parser.add_argument("--data", default=None, help="Override data file path")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--days", nargs="*", help="Specific days to render (YYYY-MM-DD)")
    parser.add_argument("--width", type=int, default=1800, help="Frame width")
    parser.add_argument("--height", type=int, default=1200, help="Frame height")
    parser.add_argument("--fps", type=float, default=32.0, help="Frames per second")
    parser.add_argument("--list-sites", action="store_true", help="List available sites and exit")
    args = parser.parse_args()

    # List sites if requested
    if args.list_sites:
        print("Available sites:")
        for site_name in list_available_sites():
            config = get_site_config(site_name)
            print(f"  {site_name}: {config.display_name}")
            for pt in config.pollution_types:
                print(f"    - {pt.name}: {pt.display_name}")
        return

    # Get site config
    try:
        site_config = get_site_config(args.site)
    except ValueError as e:
        print(f"Error: {e}")
        return

    print("\n" + "="*60)
    print(f"  Air Quality Animation Renderer")
    print("="*60)
    print(f"Site: {site_config.display_name}")
    print(f"Features:")
    print("  • Pollution circles (size + color)")
    print("  • Wind arrows from each sensor")
    print("  • Single combined video per pollution type")
    print()

    total_start = time.time()

    # Determine which pollution types to render
    if args.pollution:
        # Find specific pollution type
        pollution_types = [pt for pt in site_config.pollution_types if pt.name == args.pollution]
        if not pollution_types:
            available = ", ".join(pt.name for pt in site_config.pollution_types)
            print(f"Error: Unknown pollution type '{args.pollution}'. Available: {available}")
            return
    elif args.all:
        # Render all pollution types
        pollution_types = site_config.pollution_types
    else:
        # Default: first pollution type
        pollution_types = [site_config.pollution_types[0]]

    print(f"Pollution types to render: {', '.join(pt.name for pt in pollution_types)}")

    # Load data
    data_file = args.data or site_config.data_file
    print(f"\nLoading data from: {data_file}")
    df = load_rds_data(data_file)

    # Add timestamp column using site's column mapping
    timestamp_col = site_config.column_mapping.timestamp
    if timestamp_col not in df.columns:
        # Fallback search
        for col in ['timestamp_local.x', 'timestamp_local.y', 'timestamp_local', 'timestamp', 'valid']:
            if col in df.columns:
                timestamp_col = col
                break
    df['timestamp'] = pd.to_datetime(df[timestamp_col], errors='coerce')

    # Get dates
    if args.days:
        dates = args.days
    else:
        dates = get_available_dates(df, site_config)

    print(f"\nDays to process: {len(dates)}")
    for d in dates[:5]:  # Show first 5
        print(f"  • {d}")
    if len(dates) > 5:
        print(f"  ... and {len(dates) - 5} more")

    # Render - weekly or single video
    if args.weekly:
        all_results = render_weekly(site_config, pollution_types, df, dates, args)

        # Summary for weekly
        elapsed = time.time() - total_start

        print("\n" + "="*60)
        print("  Complete!")
        print("="*60)
        print(f"\nTotal time: {elapsed:.1f}s ({elapsed/60:.1f} min)")

        # Group results by week
        weeks_rendered = set()
        total_frames = 0
        videos_created = 0
        for result in all_results:
            weeks_rendered.add(result.get('week'))
            if not result.get('skipped', False):
                total_frames += result.get('total_frames', 0)
                if result.get('video_file'):
                    videos_created += 1

        print(f"\nWeeks processed: {len(weeks_rendered)}")
        print(f"Videos created: {videos_created}")
        print(f"Total frames rendered: {total_frames}")
        print(f"\nOutput: {Path(args.output) / 'videos' / site_config.name}/")
    else:
        # Original single-video mode
        all_results = []
        for pollution_type in pollution_types:
            result = render_animation(site_config, pollution_type, df, dates, args)
            result['pollution_type'] = pollution_type
            all_results.append(result)

        # Summary
        elapsed = time.time() - total_start

        print("\n" + "="*60)
        print("  Complete!")
        print("="*60)
        print(f"\nTotal time: {elapsed:.1f}s ({elapsed/60:.1f} min)")

        for result in all_results:
            pt = result['pollution_type']
            print(f"\n{pt.display_name}:")
            print(f"  Frames: {result['total_frames']}")
            if result['video_file']:
                print(f"  Video: {result['video_file']}")
            if result['day_stats']:
                print(f"  Days rendered: {len(result['day_stats'])}")


if __name__ == "__main__":
    main()
