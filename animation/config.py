"""Configuration for UFP Animation Pipeline."""

from dataclasses import dataclass
from typing import Optional

@dataclass
class MapExtent:
    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float

    @property
    def lon_center(self) -> float:
        return (self.lon_min + self.lon_max) / 2

    @property
    def lat_center(self) -> float:
        return (self.lat_min + self.lat_max) / 2

@dataclass
class SensorCoord:
    sensor: str
    lat: float
    lon: float

# Sensor coordinates
SENSOR_COORDS = [
    SensorCoord("MOD-UFP-00007", 42.36148, -70.97251),
    SensorCoord("MOD-UFP-00008", 42.38407, -71.00227),
    SensorCoord("MOD-UFP-00009", 42.36407, -71.02910),
]

# Calculate map extent from sensor coordinates
def calculate_map_extent(sensors: list[SensorCoord], padding: float = 0.005) -> MapExtent:
    lats = [s.lat for s in sensors]
    lons = [s.lon for s in sensors]

    lat_center = sum(lats) / len(lats)
    lon_center = sum(lons) / len(lons)
    lat_range = max(lats) - min(lats)
    lon_range = max(lons) - min(lons)

    lat_padding = max(padding, lat_range * 0.05)
    lon_padding = max(padding, lon_range * 0.05)

    return MapExtent(
        lon_min=lon_center - lon_range/2 - lon_padding,
        lon_max=lon_center + lon_range/2 + lon_padding,
        lat_min=lat_center - lat_range/2 - lat_padding,
        lat_max=lat_center + lat_range/2 + lat_padding,
    )

MAP_EXTENT = calculate_map_extent(SENSOR_COORDS)

@dataclass
class Config:
    data_path: str = "../animation/data/Eastie_UFP.rds"
    target_date: str = "2025-08-01"
    title_date: str = "August 1, 2025"
    output_dir: str = "out"
    seconds_per_frame: float = 0.5  # 2x faster animation
    width: int = 1800
    height: int = 1200
    cleanup_frames: bool = False
