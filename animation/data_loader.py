"""Data loading and processing for multi-site air quality animation."""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import NamedTuple, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from site_config import SiteConfig, PollutionType

try:
    import pyreadr
    HAS_PYREADR = True
except ImportError:
    HAS_PYREADR = False


class ProcessedData(NamedTuple):
    animation_data: pd.DataFrame
    wind_summary: pd.DataFrame
    unique_times: list
    pollution_stats: dict


def load_rds_data(filepath: str) -> pd.DataFrame:
    """Load data from RDS file."""
    if not HAS_PYREADR:
        raise ImportError("pyreadr is required to read RDS files. Install with: pip install pyreadr")

    result = pyreadr.read_r(filepath)
    # RDS files contain a single dataframe
    df = list(result.values())[0]
    return df


def process_data(df: pd.DataFrame, target_date: str, site_config: 'SiteConfig',
                 pollution_type: 'PollutionType') -> ProcessedData:
    """Process raw data for animation.

    Args:
        df: Raw dataframe with pollution and wind data
        target_date: Date string in YYYY-MM-DD format
        site_config: Site configuration object
        pollution_type: Pollution type configuration
    """
    col_map = site_config.column_mapping

    # Use configured timestamp column
    timestamp_col = col_map.timestamp
    if timestamp_col not in df.columns:
        # Fallback search for timestamp column
        for col in ['timestamp_local.x', 'timestamp_local.y', 'timestamp_local', 'timestamp', 'valid']:
            if col in df.columns:
                timestamp_col = col
                break
        else:
            raise ValueError(f"Could not find timestamp column '{col_map.timestamp}' in data")

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df[timestamp_col])

    # Filter to target date
    target = pd.to_datetime(target_date).date()
    df = df[df['timestamp'].dt.date == target].copy()

    print(f"Filtered data for {target_date} ({site_config.display_name} - {pollution_type.display_name}):")
    print(f"  Total observations: {len(df)}")

    if len(df) == 0:
        raise ValueError(f"No data found for date {target_date}")

    # Create time groups (round to 5 minutes)
    df['time_group'] = df['timestamp'].dt.floor('5min')

    # Use configured pollution column
    pollution_col = pollution_type.column
    if pollution_col not in df.columns:
        raise ValueError(f"Pollution column '{pollution_col}' not found in data. "
                        f"Available columns: {list(df.columns)}")

    df['pollution'] = pd.to_numeric(df[pollution_col], errors='coerce')

    # Get sensor coordinates as dict for lookup
    sensor_dict = {s.sensor: (s.lat, s.lon) for s in site_config.sensors}

    # Use configured sensor ID column
    sensor_col = col_map.sensor_id
    if sensor_col not in df.columns:
        # Fallback search
        for col in ['sn.x', 'sn.y', 'sn', 'sensor_id', 'sensor', 'device_id']:
            if col in df.columns:
                sensor_col = col
                break
        else:
            sensor_col = None

    # Use sensor ID to get lat/lon from config (more reliable than data columns)
    if sensor_col:
        df['sensor_id'] = df[sensor_col]
        df['lat'] = df[sensor_col].map(lambda x: sensor_dict.get(x, (None, None))[0])
        df['lon'] = df[sensor_col].map(lambda x: sensor_dict.get(x, (None, None))[1])
    else:
        # Fallback to lat/lon columns in data or config
        if col_map.geo_lat and col_map.geo_lat in df.columns:
            df['lat'] = df[col_map.geo_lat]
        elif 'lat' not in df.columns or df['lat'].isna().all():
            for lat_col in ['geo.lat', 'met_lat_ASOS']:
                if lat_col in df.columns and not df[lat_col].isna().all():
                    df['lat'] = df[lat_col]
                    break

        if col_map.geo_lon and col_map.geo_lon in df.columns:
            df['lon'] = df[col_map.geo_lon]
        elif 'lon' not in df.columns or df['lon'].isna().all():
            for lon_col in ['geo.lon', 'met_lon_ASOS']:
                if lon_col in df.columns and not df[lon_col].isna().all():
                    df['lon'] = df[lon_col]
                    break

    # Drop rows with missing essential data
    df = df.dropna(subset=['pollution', 'lat', 'lon'])

    if len(df) == 0:
        raise ValueError("No valid data after filtering (missing pollution or coordinates)")

    # Aggregate by time, location, and sensor_id
    group_cols = ['time_group', 'lat', 'lon']
    if 'sensor_id' in df.columns:
        group_cols.append('sensor_id')

    animation_data = df.groupby(group_cols).agg({
        'pollution': 'mean'
    }).reset_index()

    # Process wind data using configured columns
    wind_dir_col = col_map.wind_dir
    wind_speed_col = col_map.wind_speed

    # Look for wind U/V components or direction/speed
    wind_u_col = None
    wind_v_col = None

    for col in ['met_wx_u', 'met.wx_u', 'wind_u']:
        if col in df.columns:
            wind_u_col = col
            break

    for col in ['met_wx_v', 'met.wx_v', 'wind_v']:
        if col in df.columns:
            wind_v_col = col
            break

    # Find wind speed column (use config or search)
    if wind_speed_col not in df.columns:
        for col in ['met_wx_ws', 'met.wx_ws', 'ws', 'wind_speed']:
            if col in df.columns:
                wind_speed_col = col
                break
        else:
            wind_speed_col = None

    if wind_u_col and wind_v_col and wind_speed_col:
        wind_summary = df.groupby('time_group').agg({
            wind_u_col: 'mean',
            wind_v_col: 'mean',
            wind_speed_col: 'mean',
        }).reset_index()
        wind_summary.columns = ['time_group', 'avg_wind_u', 'avg_wind_v', 'avg_wind_speed']
    elif wind_dir_col in df.columns and wind_speed_col:
        # Compute U/V from direction and speed
        wind_data = df.groupby('time_group').agg({
            wind_dir_col: 'mean',
            wind_speed_col: 'mean',
        }).reset_index()
        wind_data.columns = ['time_group', 'avg_wind_dir', 'avg_wind_speed']
        # Convert direction to U/V (meteorological convention: direction wind is FROM)
        wind_dir_rad = np.radians(wind_data['avg_wind_dir'])
        wind_data['avg_wind_u'] = -wind_data['avg_wind_speed'] * np.sin(wind_dir_rad)
        wind_data['avg_wind_v'] = -wind_data['avg_wind_speed'] * np.cos(wind_dir_rad)
        wind_summary = wind_data[['time_group', 'avg_wind_u', 'avg_wind_v', 'avg_wind_speed']]
    else:
        # Create empty wind summary
        unique_times = sorted(animation_data['time_group'].unique())
        wind_summary = pd.DataFrame({
            'time_group': unique_times,
            'avg_wind_u': [0.0] * len(unique_times),
            'avg_wind_v': [0.0] * len(unique_times),
            'avg_wind_speed': [0.0] * len(unique_times),
        })

    unique_times = sorted(animation_data['time_group'].unique())

    # Calculate pollution statistics
    pollution_min = animation_data['pollution'].min()
    pollution_max = animation_data['pollution'].max()

    # Create nice breaks for legend based on pollution type's vis range
    vis_range = pollution_type.vis_max - pollution_type.vis_min
    step = vis_range / 4
    breaks = [pollution_type.vis_min + i * step for i in range(5)]

    pollution_stats = {
        'min': pollution_min,
        'max': pollution_max,
        'vis_min': pollution_type.vis_min,
        'vis_max': pollution_type.vis_max,
        'breaks': breaks,
    }

    print(f"  Time range: {unique_times[0]} to {unique_times[-1]}")
    print(f"  Animation data prepared: {len(animation_data)} time-sensor combinations")
    print(f"  Unique time points: {len(unique_times)}")
    print(f"  Pollution range: {pollution_min:.1f} to {pollution_max:.1f} {pollution_type.unit}")

    return ProcessedData(
        animation_data=animation_data,
        wind_summary=wind_summary,
        unique_times=unique_times,
        pollution_stats=pollution_stats,
    )


# Legacy function for backwards compatibility
def process_data_legacy(df: pd.DataFrame, target_date: str, sensor_coords: list) -> ProcessedData:
    """Process raw data for animation (legacy interface).

    This maintains backwards compatibility with existing code.
    For new code, use process_data() with SiteConfig instead.
    """
    from site_config import create_eastie_config
    config = create_eastie_config()
    return process_data(df, target_date, config, config.pollution_types[0])
