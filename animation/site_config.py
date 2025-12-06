"""
Site configuration for multi-site air quality animation rendering.

This module provides a unified configuration system that allows the same
rendering pipeline to be used for different monitoring sites (East Boston, ECAGP, etc.)
and multiple pollution types per site.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import namedtuple


# Named tuple for sensor coordinates
SensorCoord = namedtuple('SensorCoord', ['sensor', 'lat', 'lon'])

# Named tuple for map extent
MapExtent = namedtuple('MapExtent', ['lat_min', 'lat_max', 'lon_min', 'lon_max'])


@dataclass
class PollutionType:
    """Configuration for a specific pollution measurement type."""
    name: str           # Short name (e.g., "pm25", "ufp")
    column: str         # Column name in data
    display_name: str   # Display name for titles (e.g., "PM2.5")
    unit: str           # Unit label (e.g., "µg/m³", "particles/cm³")
    vis_min: float      # Min value for color scale
    vis_max: float      # Max value for color scale
    video_suffix: str   # Suffix for output video filename


@dataclass
class ColumnMapping:
    """Mapping of data columns for a specific site's data format."""
    timestamp: str  # Column containing timestamps
    sensor_id: str  # Column containing sensor identifiers
    wind_dir: str   # Column containing wind direction (degrees)
    wind_speed: str # Column containing wind speed
    geo_lat: Optional[str] = None  # Column for latitude (if in data)
    geo_lon: Optional[str] = None  # Column for longitude (if in data)


@dataclass
class SiteConfig:
    """Configuration for a monitoring site."""

    # Site identification
    name: str                    # Short name (e.g., "eastie", "ecagp")
    display_name: str            # Display name for titles

    # Data configuration
    data_file: str               # Path to data file (relative to animation/)
    column_mapping: ColumnMapping

    # Pollution types for this site (can have multiple)
    pollution_types: List[PollutionType]

    # Sensor configuration
    sensors: List[SensorCoord]   # List of sensor coordinates
    sensor_display_names: Dict[str, str] = field(default_factory=dict)  # Optional display names

    # Wind configuration
    wind_speed_max: float = 4.0  # Max wind speed for visualization scaling

    # Map configuration
    map_padding: float = 0.015   # Padding around sensors in degrees
    coord_label_step: float = 0.02  # Step size for coordinate labels
    hardcoded_extent: Optional[MapExtent] = None  # Override calculated extent

    # Output configuration
    output_dir: str = "output"   # Output directory name
    base_map_file: str = "base_map.png"  # Base map filename

    # Circle sizing
    circle_min: float = 110      # Minimum circle size in pixels
    circle_max: float = 220      # Maximum circle size in pixels

    def get_map_extent(self) -> MapExtent:
        """Get map extent - use hardcoded if set, otherwise calculate from sensors."""
        if self.hardcoded_extent is not None:
            return self.hardcoded_extent
        # Calculate from sensor coordinates with padding
        lats = [s.lat for s in self.sensors]
        lons = [s.lon for s in self.sensors]
        return MapExtent(
            lat_min=min(lats) - self.map_padding,
            lat_max=max(lats) + self.map_padding,
            lon_min=min(lons) - self.map_padding,
            lon_max=max(lons) + self.map_padding
        )

    def get_sensor_display_name(self, sensor_id: str) -> str:
        """Get display name for a sensor, defaulting to sensor_id."""
        return self.sensor_display_names.get(sensor_id, sensor_id)

    def get_coord_label_ranges(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Get rounded coordinate label ranges for the map."""
        extent = self.get_map_extent()

        # Round to step size for clean labels
        lon_start = round(extent.lon_min / self.coord_label_step) * self.coord_label_step
        lon_end = round(extent.lon_max / self.coord_label_step) * self.coord_label_step
        lat_start = round(extent.lat_min / self.coord_label_step) * self.coord_label_step
        lat_end = round(extent.lat_max / self.coord_label_step) * self.coord_label_step

        return ((lon_start, lon_end), (lat_start, lat_end))

    def get_video_filename(self, pollution_type: PollutionType) -> str:
        """Get output video filename for a pollution type."""
        return f"{self.name}_{pollution_type.video_suffix}.mp4"

    def get_base_map_path(self) -> str:
        """Get full path to base map file."""
        return f"{self.output_dir}/{self.name}_{self.base_map_file}"


# ============================================================================
# Site-specific configurations
# ============================================================================

def create_eastie_config() -> SiteConfig:
    """Create configuration for East Boston UFP monitoring site."""
    return SiteConfig(
        name="eastie",
        display_name="East Boston",
        data_file="data/Eastie_UFP.rds",
        column_mapping=ColumnMapping(
            timestamp="timestamp_local.x",
            sensor_id="sn.x",
            wind_dir="met_wx_wd",
            wind_speed="met_wx_ws",
            geo_lat="geo.lat",
            geo_lon="geo.lon"
        ),
        pollution_types=[
            PollutionType(
                name="ufp",
                column="cpc_particle_number_conc_corr.x",
                display_name="Ultrafine Particle Pollution (UFP)",
                unit="particles/cm³",
                vis_min=2000,
                vis_max=150000,
                video_suffix="ufp"
            ),
        ],
        sensors=[
            SensorCoord("MOD-UFP-00007", 42.36148, -70.97251),
            SensorCoord("MOD-UFP-00008", 42.38407, -71.00227),
            SensorCoord("MOD-UFP-00009", 42.36407, -71.02910),
        ],
        sensor_display_names={
            "MOD-UFP-00007": "MOD-UFP-00007",
            "MOD-UFP-00008": "MOD-UFP-00008",
            "MOD-UFP-00009": "MOD-UFP-00009",
        },
        wind_speed_max=4.0,
        output_dir="output",
    )


def create_ecagp_config() -> SiteConfig:
    """Create configuration for ECAGP PM monitoring site (Galena Park, Houston area).

    NOTE: The ECAGP data does not contain per-sensor lat/lon coordinates.
    Sensor coordinates must be provided manually in this config.

    Map extent hardcoded to show area from:
      NW: 29.761700, -95.259817 (Clinton Park Tri-Community)
      SE: 29.721406, -95.202621 (111 Shaver St, Pasadena)
    """
    return SiteConfig(
        name="ecagp",
        display_name="Galena Park",
        data_file="data/ECAGP.rds",
        column_mapping=ColumnMapping(
            timestamp="timestamp",
            sensor_id="sensor_id",
            wind_dir="wd",
            wind_speed="ws",
            geo_lat=None,  # Not in data - coords from config
            geo_lon=None   # Not in data - coords from config
        ),
        pollution_types=[
            PollutionType(
                name="pm1",
                column="pm1",
                display_name="PM1 Particulate Matter",
                unit="µg/m³",
                vis_min=0,
                vis_max=50,
                video_suffix="pm1"
            ),
            PollutionType(
                name="pm25",
                column="pm25",
                display_name="PM2.5 Particulate Matter",
                unit="µg/m³",
                vis_min=0,
                vis_max=100,
                video_suffix="pm25"
            ),
            PollutionType(
                name="pm10",
                column="pm10",
                display_name="PM10 Particulate Matter",
                unit="µg/m³",
                vis_min=0,
                vis_max=200,
                video_suffix="pm10"
            ),
        ],
        sensors=[
            SensorCoord("MOD-PM-01396", 29.7326, -95.2365),  # Clinton Site (Gia)
            SensorCoord("MOD-PM-01395", 29.7342, -95.2418),  # Eastway Site (Isa)
        ],
        sensor_display_names={
            "MOD-PM-01396": "MOD-PM-01396",
            "MOD-PM-01395": "MOD-PM-01395",
        },
        circle_min=70,   # Smaller circles since sensors are close together
        circle_max=140,
        wind_speed_max=6.0,
        coord_label_step=0.02,
        # Hardcoded map extent (expanded view):
        # North: Jacinto City / I-10
        # South: Harrisburg / south of Buffalo Bayou
        # West: Trimmed to focus on Galena Park area
        # East: Greens Port / ship channel
        hardcoded_extent=MapExtent(
            lat_min=29.705,
            lat_max=29.77,
            lon_min=-95.26,
            lon_max=-95.145
        ),
        output_dir="output",
    )


def get_site_config(site_name: str) -> SiteConfig:
    """Get configuration for a site by name."""
    configs = {
        "eastie": create_eastie_config,
        "ecagp": create_ecagp_config,
    }

    if site_name not in configs:
        available = ", ".join(configs.keys())
        raise ValueError(f"Unknown site '{site_name}'. Available sites: {available}")

    return configs[site_name]()


def list_available_sites() -> List[str]:
    """List all available site names."""
    return ["eastie", "ecagp"]
