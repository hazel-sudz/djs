"""
Data processing for multi-site pollution visualization with per-sensor wind vectors.

Uses wind direction (wd) and speed (ws) directly.
"""

import pandas as pd
import numpy as np
from typing import NamedTuple, Optional, TYPE_CHECKING
import math

if TYPE_CHECKING:
    from site_config import SiteConfig, PollutionType


class FrameData(NamedTuple):
    """Frame data with sensor pollution and wind vectors."""
    timestamp: pd.Timestamp
    date_label: str
    time_label: str

    # Per-sensor data: [(lon, lat, pollution, wind_dir, wind_speed, sensor_id), ...]
    sensors: list


def gaussian_kernel_smooth(times: np.ndarray, values: np.ndarray,
                           target_times: np.ndarray, sigma_minutes: float = 10.0) -> np.ndarray:
    """Apply Gaussian kernel smoothing to time series data."""
    sigma_seconds = sigma_minutes * 60
    smoothed = np.zeros(len(target_times))

    for i, t in enumerate(target_times):
        time_diffs = np.abs(times - t)
        weights = np.exp(-0.5 * (time_diffs / sigma_seconds) ** 2)

        mask = time_diffs < 3 * sigma_seconds
        if mask.sum() > 0:
            smoothed[i] = np.average(values[mask], weights=weights[mask])
        else:
            nearest_idx = np.argmin(time_diffs)
            smoothed[i] = values[nearest_idx]

    return smoothed


def circular_mean(directions: np.ndarray, weights: np.ndarray = None) -> float:
    """Calculate circular mean of wind directions (in degrees)."""
    if len(directions) == 0:
        return 0.0

    # Convert to radians
    rads = np.radians(directions)

    if weights is None:
        weights = np.ones(len(directions))

    # Calculate weighted mean of sin and cos components
    sin_sum = np.sum(weights * np.sin(rads))
    cos_sum = np.sum(weights * np.cos(rads))

    # Convert back to degrees
    mean_rad = np.arctan2(sin_sum, cos_sum)
    mean_deg = np.degrees(mean_rad)

    if mean_deg < 0:
        mean_deg += 360

    return mean_deg


def smooth_wind_direction(times: np.ndarray, directions: np.ndarray,
                          target_times: np.ndarray, sigma_minutes: float = 10.0) -> np.ndarray:
    """Apply Gaussian kernel smoothing to wind direction (circular variable)."""
    sigma_seconds = sigma_minutes * 60
    smoothed = np.zeros(len(target_times))

    for i, t in enumerate(target_times):
        time_diffs = np.abs(times - t)
        weights = np.exp(-0.5 * (time_diffs / sigma_seconds) ** 2)

        mask = time_diffs < 3 * sigma_seconds
        if mask.sum() > 0:
            smoothed[i] = circular_mean(directions[mask], weights[mask])
        else:
            nearest_idx = np.argmin(time_diffs)
            smoothed[i] = directions[nearest_idx]

    return smoothed


def process_day(df: pd.DataFrame, target_date: str, site_config: 'SiteConfig',
                pollution_type: 'PollutionType',
                frame_interval_minutes: float = 5.0,
                smoothing_sigma_minutes: float = 10.0) -> list:
    """
    Process a day's data with simple sensor-level analysis.

    Args:
        df: DataFrame with pollution and wind data (timestamp column already processed)
        target_date: Date string in YYYY-MM-DD format
        site_config: Site configuration object
        pollution_type: Pollution type configuration
        frame_interval_minutes: Interval between frames in minutes
        smoothing_sigma_minutes: Gaussian smoothing sigma in minutes

    Returns:
        List of FrameData objects
    """
    col_map = site_config.column_mapping

    # Filter to target date
    target = pd.to_datetime(target_date).date()
    df = df[df['timestamp'].dt.date == target].copy()

    if len(df) == 0:
        return []

    # Get sensor info from config
    sensor_dict = {s.sensor: (s.lat, s.lon) for s in site_config.sensors}

    # Find and map sensor ID column
    sensor_col = col_map.sensor_id
    if sensor_col not in df.columns:
        for col in ['sn.x', 'sn.y', 'sn', 'sensor_id', 'sensor', 'device_id']:
            if col in df.columns:
                sensor_col = col
                break
        else:
            raise ValueError(f"Could not find sensor ID column '{col_map.sensor_id}' in data")

    df['sensor_id'] = df[sensor_col]
    df['lat'] = df['sensor_id'].map(lambda x: sensor_dict.get(x, (None, None))[0])
    df['lon'] = df['sensor_id'].map(lambda x: sensor_dict.get(x, (None, None))[1])

    # Pollution column from config
    pollution_col = pollution_type.column
    if pollution_col not in df.columns:
        raise ValueError(f"Pollution column '{pollution_col}' not found in data")
    df['pollution'] = pd.to_numeric(df[pollution_col], errors='coerce')

    # Wind columns from config
    wind_dir_col = col_map.wind_dir
    wind_speed_col = col_map.wind_speed

    if wind_dir_col in df.columns:
        df['wind_dir'] = pd.to_numeric(df[wind_dir_col], errors='coerce')
    else:
        # Try fallback columns
        for col in ['met_wx_wd', 'wd', 'wind_dir', 'wind_direction']:
            if col in df.columns:
                df['wind_dir'] = pd.to_numeric(df[col], errors='coerce')
                break
        else:
            df['wind_dir'] = np.nan

    if wind_speed_col in df.columns:
        df['wind_speed'] = pd.to_numeric(df[wind_speed_col], errors='coerce')
    else:
        # Try fallback columns
        for col in ['met_wx_ws', 'ws', 'wind_speed']:
            if col in df.columns:
                df['wind_speed'] = pd.to_numeric(df[col], errors='coerce')
                break
        else:
            df['wind_speed'] = np.nan

    # Drop invalid rows
    df = df.dropna(subset=['pollution', 'lat', 'lon', 'sensor_id'])

    # Filter outliers - cap at P99 and remove spikes
    if len(df) > 0:
        p99 = df['pollution'].quantile(0.99)
        df['rolling_median'] = df.groupby('sensor_id')['pollution'].transform(
            lambda x: x.rolling(window=5, min_periods=1, center=True).median()
        )
        spike_mask = (df['pollution'] / df['rolling_median'].clip(lower=1)) <= 50
        df = df[(df['pollution'] <= p99) & spike_mask]
        df = df.drop(columns=['rolling_median'])

    # Also filter extreme wind speeds (use config's wind_speed_max)
    wind_cap = site_config.wind_speed_max * 1.25  # Allow 25% above max for filtering
    if len(df) > 0:
        df = df[df['wind_speed'].isna() | (df['wind_speed'] <= wind_cap)]

    if len(df) == 0:
        return []

    # Get time range
    time_min = df['timestamp'].min()
    time_max = df['timestamp'].max()

    # Generate output frame times
    frame_times = pd.date_range(
        start=time_min.ceil('5min'),
        end=time_max.floor('5min'),
        freq=f'{int(frame_interval_minutes)}min'
    )

    # Process each sensor's time series
    sensors = df['sensor_id'].unique()
    sensor_data = {}

    for sensor in sensors:
        sensor_df = df[df['sensor_id'] == sensor].sort_values('timestamp')

        if len(sensor_df) < 3:
            continue

        times_numeric = sensor_df['timestamp'].astype(np.int64) / 1e9
        target_times_numeric = frame_times.astype(np.int64) / 1e9

        # Smooth pollution values
        smoothed_pollution = gaussian_kernel_smooth(
            times_numeric.values,
            sensor_df['pollution'].values,
            target_times_numeric.values,
            sigma_minutes=smoothing_sigma_minutes
        )

        # Get coordinates
        lat = sensor_df['lat'].iloc[0]
        lon = sensor_df['lon'].iloc[0]

        # Process wind data for this sensor
        wind_df = sensor_df.dropna(subset=['wind_dir', 'wind_speed'])

        if len(wind_df) > 0:
            wind_times = wind_df['timestamp'].astype(np.int64) / 1e9

            # Smooth wind speed (linear)
            smoothed_wind_speed = gaussian_kernel_smooth(
                wind_times.values, wind_df['wind_speed'].values,
                target_times_numeric.values, sigma_minutes=smoothing_sigma_minutes
            )

            # Smooth wind direction (circular)
            smoothed_wind_dir = smooth_wind_direction(
                wind_times.values, wind_df['wind_dir'].values,
                target_times_numeric.values, sigma_minutes=smoothing_sigma_minutes
            )
        else:
            smoothed_wind_speed = np.zeros(len(frame_times))
            smoothed_wind_dir = np.zeros(len(frame_times))

        sensor_data[sensor] = {
            'lat': lat,
            'lon': lon,
            'pollution': smoothed_pollution,
            'wind_dir': smoothed_wind_dir,
            'wind_speed': smoothed_wind_speed
        }

    # Build frame data
    frames = []
    date_label = pd.to_datetime(target_date).strftime("%B %d, %Y")

    for i, frame_time in enumerate(frame_times):
        sensors_list = []

        for sensor_id, data in sensor_data.items():
            sensors_list.append((
                data['lon'],
                data['lat'],
                data['pollution'][i],
                data['wind_dir'][i],
                data['wind_speed'][i],
                sensor_id
            ))

        if len(sensors_list) == 0:
            continue

        frames.append(FrameData(
            timestamp=frame_time,
            date_label=date_label,
            time_label=frame_time.strftime("%H:%M"),
            sensors=sensors_list
        ))

    return frames


# Legacy function for backwards compatibility
def process_day_legacy(df: pd.DataFrame, target_date: str, sensor_coords: list,
                       frame_interval_minutes: float = 5.0,
                       smoothing_sigma_minutes: float = 10.0) -> list:
    """Legacy interface for process_day. Use process_day() with SiteConfig instead."""
    from site_config import create_eastie_config
    config = create_eastie_config()
    return process_day(df, target_date, config, config.pollution_types[0],
                       frame_interval_minutes, smoothing_sigma_minutes)


def get_pollution_stats(frames: list) -> dict:
    """Get min/max pollution across all frames for consistent scaling."""
    all_pollution = []
    for frame in frames:
        for sensor in frame.sensors:
            all_pollution.append(sensor[2])  # pollution value

    if len(all_pollution) == 0:
        return {'min': 0, 'max': 100000}

    return {
        'min': min(all_pollution),
        'max': max(all_pollution)
    }
