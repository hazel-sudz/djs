"""Data loading and processing for UFP animation."""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import NamedTuple
from pathlib import Path

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


def process_data(df: pd.DataFrame, target_date: str, sensor_coords: list) -> ProcessedData:
    """Process raw data for animation.

    Args:
        df: Raw dataframe with pollution and wind data
        target_date: Date string in YYYY-MM-DD format
        sensor_coords: List of SensorCoord objects
    """
    # Identify timestamp column
    timestamp_col = None
    for col in ['timestamp_local.x', 'timestamp_local.y', 'timestamp_local', 'timestamp', 'valid']:
        if col in df.columns:
            timestamp_col = col
            break

    if timestamp_col is None:
        raise ValueError("Could not find timestamp column")

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df[timestamp_col])

    # Filter to target date
    target = pd.to_datetime(target_date).date()
    df = df[df['timestamp'].dt.date == target].copy()

    print(f"Filtered data for {target_date}:")
    print(f"  Total observations: {len(df)}")

    if len(df) == 0:
        raise ValueError(f"No data found for date {target_date}")

    # Create time groups (round to 5 minutes)
    df['time_group'] = df['timestamp'].dt.floor('5min')

    # Identify pollution column
    pollution_col = None
    for col in ['cpc_particle_number_conc_corr.x', 'cpc_particle_number_conc_corr.y',
                'cpc_particle_number_conc_corr', 'conc', 'concentration', 'pollution', 'ufp', 'value']:
        if col in df.columns:
            pollution_col = col
            break

    if pollution_col is None:
        raise ValueError("Could not identify pollution column in data")

    df['pollution'] = pd.to_numeric(df[pollution_col], errors='coerce')

    # Get sensor coordinates as dict for lookup
    sensor_dict = {s.sensor: (s.lat, s.lon) for s in sensor_coords}

    # Try to find sensor ID column
    sensor_col = None
    for col in ['sn.x', 'sn.y', 'sn', 'sensor_id', 'sensor', 'device_id']:
        if col in df.columns:
            sensor_col = col
            break

    # Use sensor ID to get lat/lon from config (more reliable than data columns)
    if sensor_col:
        df['sensor_id'] = df[sensor_col]
        df['lat'] = df[sensor_col].map(lambda x: sensor_dict.get(x, (None, None))[0])
        df['lon'] = df[sensor_col].map(lambda x: sensor_dict.get(x, (None, None))[1])
    else:
        # Fallback to lat/lon columns in data
        if 'lat' not in df.columns or df['lat'].isna().all():
            for lat_col in ['geo.lat', 'met_lat_ASOS']:
                if lat_col in df.columns and not df[lat_col].isna().all():
                    df['lat'] = df[lat_col]
                    break

        if 'lon' not in df.columns or df['lon'].isna().all():
            for lon_col in ['geo.lon', 'met_lon_ASOS']:
                if lon_col in df.columns and not df[lon_col].isna().all():
                    df['lon'] = df[lon_col]
                    break

    # Drop rows with missing essential data
    df = df.dropna(subset=['pollution', 'lat', 'lon'])

    if len(df) == 0:
        raise ValueError("No valid data after filtering (missing pollution or coordinates)")

    # Aggregate by time and location
    animation_data = df.groupby(['time_group', 'lat', 'lon']).agg({
        'pollution': 'mean'
    }).reset_index()

    # Process wind data
    wind_u_col = None
    wind_v_col = None
    wind_speed_col = None

    for col in ['met_wx_u', 'met.wx_u', 'wind_u']:
        if col in df.columns:
            wind_u_col = col
            break

    for col in ['met_wx_v', 'met.wx_v', 'wind_v']:
        if col in df.columns:
            wind_v_col = col
            break

    for col in ['met_wx_ws', 'met.wx_ws', 'ws', 'wind_speed']:
        if col in df.columns:
            wind_speed_col = col
            break

    if wind_u_col and wind_v_col and wind_speed_col:
        wind_summary = df.groupby('time_group').agg({
            wind_u_col: 'mean',
            wind_v_col: 'mean',
            wind_speed_col: 'mean',
        }).reset_index()
        wind_summary.columns = ['time_group', 'avg_wind_u', 'avg_wind_v', 'avg_wind_speed']
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

    # Create nice breaks for legend
    breaks = [0, 50000, 100000, 150000, 200000]
    breaks = [b for b in breaks if b <= pollution_max * 1.1]

    pollution_stats = {
        'min': pollution_min,
        'max': pollution_max,
        'breaks': breaks,
    }

    print(f"  Time range: {unique_times[0]} to {unique_times[-1]}")
    print(f"  Animation data prepared: {len(animation_data)} time-sensor combinations")
    print(f"  Unique time points: {len(unique_times)}")
    print(f"  Pollution range: {pollution_min:.1f} to {pollution_max:.1f} particles/cm³")

    return ProcessedData(
        animation_data=animation_data,
        wind_summary=wind_summary,
        unique_times=unique_times,
        pollution_stats=pollution_stats,
    )
