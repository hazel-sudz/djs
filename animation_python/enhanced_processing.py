"""
Enhanced data processing with advanced smoothing and correlation analysis.

Key improvements over basic processing:
1. Gaussian temporal smoothing (not just 5-min bins)
2. Spatial interpolation (IDW) for pollution field
3. Wind-pollution correlation analysis
4. Per-sensor trend detection
"""

import pandas as pd
import numpy as np
from typing import NamedTuple, Optional
from datetime import timedelta
from scipy import ndimage
from scipy.interpolate import RBFInterpolator
import math


class EnhancedFrameData(NamedTuple):
    """Enhanced frame data with additional analysis."""
    timestamp: pd.Timestamp
    time_label: str

    # Per-sensor data
    sensors: list  # [(lon, lat, pollution, label, trend, is_upwind), ...]

    # Wind data
    wind_speed: float
    wind_direction: float  # degrees, 0=N, 90=E
    wind_u: float
    wind_v: float

    # Analysis results
    pollution_gradient_direction: float  # direction of increasing pollution
    wind_pollution_alignment: float  # -1 to 1, positive = wind carrying pollution toward high
    transport_indicator: str  # "transporting", "dispersing", "mixing"

    # Interpolated pollution field (for heatmap rendering)
    pollution_field: Optional[np.ndarray]  # 2D array of interpolated values
    field_extent: Optional[tuple]  # (x_min, x_max, y_min, y_max)


def gaussian_kernel_smooth(times: np.ndarray, values: np.ndarray,
                           target_times: np.ndarray, sigma_minutes: float = 10.0) -> np.ndarray:
    """
    Apply Gaussian kernel smoothing to time series data.

    Args:
        times: Array of timestamps (as numeric, e.g., seconds since epoch)
        values: Array of values to smooth
        target_times: Times at which to compute smoothed values
        sigma_minutes: Standard deviation of Gaussian kernel in minutes

    Returns:
        Smoothed values at target_times
    """
    sigma_seconds = sigma_minutes * 60
    smoothed = np.zeros(len(target_times))

    for i, t in enumerate(target_times):
        # Compute Gaussian weights
        time_diffs = np.abs(times - t)
        weights = np.exp(-0.5 * (time_diffs / sigma_seconds) ** 2)

        # Only use points within 3*sigma for efficiency
        mask = time_diffs < 3 * sigma_seconds
        if mask.sum() > 0:
            smoothed[i] = np.average(values[mask], weights=weights[mask])
        else:
            # Fallback to nearest value
            nearest_idx = np.argmin(time_diffs)
            smoothed[i] = values[nearest_idx]

    return smoothed


def calculate_trend(values: np.ndarray, window: int = 5) -> np.ndarray:
    """
    Calculate local trend (rate of change) for time series.

    Returns:
        Array of trend values: positive = increasing, negative = decreasing
    """
    if len(values) < 3:
        return np.zeros(len(values))

    # Simple finite difference with smoothing
    trends = np.zeros(len(values))
    half_window = window // 2

    for i in range(len(values)):
        start = max(0, i - half_window)
        end = min(len(values), i + half_window + 1)

        if end - start >= 2:
            # Linear regression slope
            x = np.arange(end - start)
            y = values[start:end]
            slope = np.polyfit(x, y, 1)[0]
            trends[i] = slope

    return trends


def interpolate_pollution_field(sensor_lons: np.ndarray, sensor_lats: np.ndarray,
                                 pollution_values: np.ndarray,
                                 extent: tuple, resolution: int = 50) -> np.ndarray:
    """
    Create interpolated pollution field using RBF interpolation.

    Args:
        sensor_lons, sensor_lats: Sensor coordinates
        pollution_values: Pollution at each sensor
        extent: (lon_min, lon_max, lat_min, lat_max)
        resolution: Grid resolution

    Returns:
        2D array of interpolated pollution values
    """
    lon_min, lon_max, lat_min, lat_max = extent

    # Create grid
    lons = np.linspace(lon_min, lon_max, resolution)
    lats = np.linspace(lat_min, lat_max, resolution)
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    # Prepare sensor coordinates
    points = np.column_stack([sensor_lons, sensor_lats])

    # RBF interpolation (handles small number of points well)
    try:
        rbf = RBFInterpolator(points, pollution_values, kernel='thin_plate_spline', smoothing=0.1)
        grid_points = np.column_stack([lon_grid.ravel(), lat_grid.ravel()])
        field = rbf(grid_points).reshape(lon_grid.shape)

        # Clip to valid range
        field = np.clip(field, pollution_values.min() * 0.5, pollution_values.max() * 1.5)
    except Exception:
        # Fallback to simple IDW
        field = idw_interpolation(sensor_lons, sensor_lats, pollution_values,
                                  lon_grid, lat_grid)

    return field


def idw_interpolation(sensor_lons: np.ndarray, sensor_lats: np.ndarray,
                       values: np.ndarray, lon_grid: np.ndarray, lat_grid: np.ndarray,
                       power: float = 2.0) -> np.ndarray:
    """
    Inverse Distance Weighting interpolation.
    """
    field = np.zeros_like(lon_grid)

    for i in range(lon_grid.shape[0]):
        for j in range(lon_grid.shape[1]):
            lon, lat = lon_grid[i, j], lat_grid[i, j]

            # Distances to all sensors
            distances = np.sqrt((sensor_lons - lon)**2 + (sensor_lats - lat)**2)

            # Handle exact sensor locations
            if distances.min() < 1e-10:
                field[i, j] = values[distances.argmin()]
            else:
                weights = 1.0 / (distances ** power)
                field[i, j] = np.sum(weights * values) / np.sum(weights)

    return field


def calculate_pollution_gradient(sensor_lons: np.ndarray, sensor_lats: np.ndarray,
                                  pollution_values: np.ndarray) -> tuple:
    """
    Calculate direction of maximum pollution increase.

    Returns:
        (gradient_direction_degrees, gradient_magnitude)
        Direction: 0=N, 90=E, 180=S, 270=W
    """
    if len(sensor_lons) < 2:
        return 0.0, 0.0

    # Fit a plane: pollution = a*lon + b*lat + c
    # Gradient direction is (a, b) normalized
    A = np.column_stack([sensor_lons, sensor_lats, np.ones(len(sensor_lons))])
    try:
        coeffs, _, _, _ = np.linalg.lstsq(A, pollution_values, rcond=None)
        grad_lon, grad_lat = coeffs[0], coeffs[1]
    except:
        return 0.0, 0.0

    magnitude = np.sqrt(grad_lon**2 + grad_lat**2)
    if magnitude < 1e-10:
        return 0.0, 0.0

    # Convert to compass direction (0=N, 90=E)
    # Note: atan2(x, y) for compass, where x=East, y=North
    direction_rad = math.atan2(grad_lon, grad_lat)
    direction_deg = math.degrees(direction_rad)
    if direction_deg < 0:
        direction_deg += 360

    return direction_deg, magnitude


def analyze_wind_pollution_relationship(wind_u: float, wind_v: float,
                                         gradient_direction: float) -> tuple:
    """
    Analyze relationship between wind and pollution gradient.

    Returns:
        (alignment, transport_indicator)
        alignment: -1 to 1
            +1 = wind blowing toward higher pollution (accumulating)
            -1 = wind blowing toward lower pollution (dispersing)
             0 = wind perpendicular to gradient (mixing)
    """
    if abs(wind_u) < 0.01 and abs(wind_v) < 0.01:
        return 0.0, "calm"

    # Wind direction (where wind is going TO, not from)
    wind_dir_rad = math.atan2(wind_u, wind_v)
    wind_dir_deg = math.degrees(wind_dir_rad)
    if wind_dir_deg < 0:
        wind_dir_deg += 360

    # Calculate alignment (cosine of angle between wind and gradient)
    angle_diff = math.radians(gradient_direction - wind_dir_deg)
    alignment = math.cos(angle_diff)

    # Determine transport indicator
    if alignment > 0.5:
        indicator = "accumulating"  # Wind pushing toward high pollution area
    elif alignment < -0.5:
        indicator = "dispersing"    # Wind pushing toward low pollution area
    else:
        indicator = "mixing"        # Cross-wind mixing

    return alignment, indicator


def determine_upwind_sensor(sensor_lons: np.ndarray, sensor_lats: np.ndarray,
                            wind_u: float, wind_v: float) -> np.ndarray:
    """
    Determine which sensors are upwind vs downwind.

    Returns:
        Array of "upwindness" scores (-1 = most downwind, +1 = most upwind)
    """
    if abs(wind_u) < 0.01 and abs(wind_v) < 0.01:
        return np.zeros(len(sensor_lons))

    # Center point
    center_lon = np.mean(sensor_lons)
    center_lat = np.mean(sensor_lats)

    # Vector from center to each sensor
    rel_lons = sensor_lons - center_lon
    rel_lats = sensor_lats - center_lat

    # Wind direction vector (normalized)
    wind_mag = np.sqrt(wind_u**2 + wind_v**2)
    wind_unit_u = wind_u / wind_mag
    wind_unit_v = wind_v / wind_mag

    # Project sensor positions onto wind direction
    # Positive = downwind, Negative = upwind
    projections = rel_lons * wind_unit_u + rel_lats * wind_unit_v

    # Normalize to -1 to 1
    if projections.max() - projections.min() > 1e-10:
        upwindness = -projections / max(abs(projections.max()), abs(projections.min()))
    else:
        upwindness = np.zeros(len(sensor_lons))

    return upwindness


def process_day_enhanced(df: pd.DataFrame, target_date: str, sensor_coords: list,
                         map_extent, frame_interval_minutes: float = 5.0,
                         smoothing_sigma_minutes: float = 10.0) -> list:
    """
    Process a day's data with enhanced analysis.

    Args:
        df: Raw dataframe
        target_date: Date string (YYYY-MM-DD)
        sensor_coords: List of SensorCoord objects
        map_extent: MapExtent object
        frame_interval_minutes: Time between output frames
        smoothing_sigma_minutes: Gaussian smoothing width

    Returns:
        List of EnhancedFrameData objects
    """
    # Filter to target date
    target = pd.to_datetime(target_date).date()
    df = df[df['timestamp'].dt.date == target].copy()

    if len(df) == 0:
        return []

    # Get sensor info
    sensor_dict = {s.sensor: (s.lat, s.lon) for s in sensor_coords}

    # Identify columns
    pollution_col = 'cpc_particle_number_conc_corr.x'

    # Map sensor coordinates
    df['sensor_id'] = df['sn.x']
    df['lat'] = df['sensor_id'].map(lambda x: sensor_dict.get(x, (None, None))[0])
    df['lon'] = df['sensor_id'].map(lambda x: sensor_dict.get(x, (None, None))[1])
    df['pollution'] = pd.to_numeric(df[pollution_col], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['pollution', 'lat', 'lon', 'sensor_id'])

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

        # Calculate trends
        trends = calculate_trend(smoothed_pollution, window=5)

        # Get coordinates
        lat = sensor_df['lat'].iloc[0]
        lon = sensor_df['lon'].iloc[0]

        sensor_data[sensor] = {
            'lat': lat,
            'lon': lon,
            'pollution': smoothed_pollution,
            'trends': trends
        }

    # Process wind data (single time series since it's from one station)
    wind_df = df[['timestamp', 'met_wx_u', 'met_wx_v', 'met_wx_ws']].drop_duplicates('timestamp').sort_values('timestamp')
    wind_df = wind_df.dropna()

    if len(wind_df) > 0:
        wind_times_numeric = wind_df['timestamp'].astype(np.int64) / 1e9
        target_times_numeric = frame_times.astype(np.int64) / 1e9

        smoothed_wind_u = gaussian_kernel_smooth(
            wind_times_numeric.values, wind_df['met_wx_u'].values,
            target_times_numeric.values, sigma_minutes=smoothing_sigma_minutes
        )
        smoothed_wind_v = gaussian_kernel_smooth(
            wind_times_numeric.values, wind_df['met_wx_v'].values,
            target_times_numeric.values, sigma_minutes=smoothing_sigma_minutes
        )
        smoothed_wind_speed = gaussian_kernel_smooth(
            wind_times_numeric.values, wind_df['met_wx_ws'].values,
            target_times_numeric.values, sigma_minutes=smoothing_sigma_minutes
        )
    else:
        smoothed_wind_u = np.zeros(len(frame_times))
        smoothed_wind_v = np.zeros(len(frame_times))
        smoothed_wind_speed = np.zeros(len(frame_times))

    # Build frame data
    frames = []
    extent = (map_extent.lon_min, map_extent.lon_max, map_extent.lat_min, map_extent.lat_max)

    for i, frame_time in enumerate(frame_times):
        # Collect sensor values for this frame
        sensor_lons = []
        sensor_lats = []
        pollution_values = []
        trend_values = []
        sensor_ids = []

        for sensor, data in sensor_data.items():
            sensor_lons.append(data['lon'])
            sensor_lats.append(data['lat'])
            pollution_values.append(data['pollution'][i])
            trend_values.append(data['trends'][i])
            sensor_ids.append(sensor)

        if len(sensor_lons) == 0:
            continue

        sensor_lons = np.array(sensor_lons)
        sensor_lats = np.array(sensor_lats)
        pollution_values = np.array(pollution_values)
        trend_values = np.array(trend_values)

        # Get wind for this frame
        wind_u = smoothed_wind_u[i]
        wind_v = smoothed_wind_v[i]
        wind_speed = smoothed_wind_speed[i]

        # Wind direction (meteorological: where wind comes FROM)
        wind_dir = math.degrees(math.atan2(-wind_u, -wind_v))
        if wind_dir < 0:
            wind_dir += 360

        # Calculate pollution gradient
        gradient_dir, gradient_mag = calculate_pollution_gradient(
            sensor_lons, sensor_lats, pollution_values
        )

        # Analyze wind-pollution relationship
        alignment, transport_indicator = analyze_wind_pollution_relationship(
            wind_u, wind_v, gradient_dir
        )

        # Determine upwind/downwind status
        upwindness = determine_upwind_sensor(sensor_lons, sensor_lats, wind_u, wind_v)

        # Create pollution field
        pollution_field = interpolate_pollution_field(
            sensor_lons, sensor_lats, pollution_values, extent, resolution=40
        )

        # Format sensor data with labels
        def format_label(val):
            if val >= 1000:
                return f"{val/1000:.1f}K"
            return f"{val:.0f}"

        def trend_symbol(trend):
            if trend > 500:
                return "↑"
            elif trend < -500:
                return "↓"
            return ""

        sensors_list = []
        for j in range(len(sensor_lons)):
            label = f"{format_label(pollution_values[j])}{trend_symbol(trend_values[j])}"
            sensors_list.append((
                sensor_lons[j],
                sensor_lats[j],
                pollution_values[j],
                label,
                trend_values[j],
                upwindness[j]
            ))

        frames.append(EnhancedFrameData(
            timestamp=frame_time,
            time_label=frame_time.strftime("%H:%M"),
            sensors=sensors_list,
            wind_speed=wind_speed,
            wind_direction=wind_dir,
            wind_u=wind_u,
            wind_v=wind_v,
            pollution_gradient_direction=gradient_dir,
            wind_pollution_alignment=alignment,
            transport_indicator=transport_indicator,
            pollution_field=pollution_field,
            field_extent=extent
        ))

    return frames


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
