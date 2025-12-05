"""
Map tile fetching and stitching for base map generation.

Fetches OpenStreetMap tiles and composites them into a single base map image.
"""

import math
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import requests
from io import BytesIO

TILE_SIZE = 256
USER_AGENT = "UFP-Animation/1.0 (Educational/Research Project)"


def deg2num(lat_deg: float, lon_deg: float, zoom: int) -> tuple[int, int]:
    """Convert lat/lon to tile numbers."""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)


def num2deg(xtile: int, ytile: int, zoom: int) -> tuple[float, float]:
    """Convert tile numbers to lat/lon (northwest corner)."""
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)


def lat_to_mercator_y(lat_deg: float, zoom: int) -> float:
    """Convert latitude to Mercator Y pixel coordinate at given zoom."""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n * TILE_SIZE
    return y


def lon_to_mercator_x(lon_deg: float, zoom: int) -> float:
    """Convert longitude to Mercator X pixel coordinate at given zoom."""
    n = 2.0 ** zoom
    x = (lon_deg + 180.0) / 360.0 * n * TILE_SIZE
    return x


def get_tile_url(x: int, y: int, zoom: int, server: str = "a") -> str:
    """Get OSM tile URL."""
    return f"https://{server}.tile.openstreetmap.org/{zoom}/{x}/{y}.png"


def fetch_tile(x: int, y: int, zoom: int, cache_dir: Path) -> Image.Image:
    """Fetch a single tile, using cache if available."""
    cache_file = cache_dir / f"{zoom}_{x}_{y}.png"

    if cache_file.exists():
        return Image.open(cache_file)

    # Rotate between servers
    servers = ["a", "b", "c"]
    server = servers[(x + y) % 3]
    url = get_tile_url(x, y, zoom, server)

    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        img = Image.open(BytesIO(response.content))

        # Cache the tile
        cache_dir.mkdir(parents=True, exist_ok=True)
        img.save(cache_file)

        return img
    except Exception as e:
        print(f"Warning: Failed to fetch tile {x},{y}: {e}")
        # Return a gray placeholder
        return Image.new('RGB', (TILE_SIZE, TILE_SIZE), (200, 200, 200))


def create_base_map(
    map_extent: 'MapExtent',
    output_path: str,
    width: int = 1800,
    height: int = 1200,
    zoom: int = 15,
    cache_dir: str = ".tile_cache"
) -> str:
    """Create base map from OSM tiles.

    Args:
        map_extent: MapExtent object with lon/lat bounds
        output_path: Path to save the output image
        width: Output image width
        height: Output image height
        zoom: OSM zoom level (15-16 for neighborhood detail)
        cache_dir: Directory to cache downloaded tiles
    """
    print("Creating base map from OSM tiles...")

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    # Calculate tile range
    min_tile = deg2num(map_extent.lat_max, map_extent.lon_min, zoom)
    max_tile = deg2num(map_extent.lat_min, map_extent.lon_max, zoom)

    x_tiles = range(min_tile[0], max_tile[0] + 1)
    y_tiles = range(min_tile[1], max_tile[1] + 1)

    n_tiles = len(x_tiles) * len(y_tiles)
    print(f"  Zoom level: {zoom}")
    print(f"  Tiles needed: {n_tiles} ({len(x_tiles)}x{len(y_tiles)})")

    # Fetch tiles in parallel
    tiles = {}
    tile_coords = [(x, y) for x in x_tiles for y in y_tiles]

    def fetch_one(coord):
        x, y = coord
        return (coord, fetch_tile(x, y, zoom, cache_path))

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(fetch_one, tile_coords))

    for coord, img in results:
        tiles[coord] = img

    # Create composite image
    composite_width = len(x_tiles) * TILE_SIZE
    composite_height = len(y_tiles) * TILE_SIZE
    composite = Image.new('RGB', (composite_width, composite_height))

    for (x, y), img in tiles.items():
        px = (x - min_tile[0]) * TILE_SIZE
        py = (y - min_tile[1]) * TILE_SIZE
        composite.paste(img, (px, py))

    # Calculate crop region using proper Mercator projection
    # Get the pixel origin of our tile grid in global Mercator coordinates
    tile_origin_x = min_tile[0] * TILE_SIZE
    tile_origin_y = min_tile[1] * TILE_SIZE

    # Convert map extent to Mercator pixel coordinates
    crop_left = int(lon_to_mercator_x(map_extent.lon_min, zoom) - tile_origin_x)
    crop_right = int(lon_to_mercator_x(map_extent.lon_max, zoom) - tile_origin_x)
    crop_top = int(lat_to_mercator_y(map_extent.lat_max, zoom) - tile_origin_y)
    crop_bottom = int(lat_to_mercator_y(map_extent.lat_min, zoom) - tile_origin_y)

    # Ensure valid crop region
    crop_left = max(0, crop_left)
    crop_top = max(0, crop_top)
    crop_right = min(composite_width, crop_right)
    crop_bottom = min(composite_height, crop_bottom)

    # Crop and resize
    cropped = composite.crop((crop_left, crop_top, crop_right, crop_bottom))
    final = cropped.resize((width, height), Image.LANCZOS)

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(output_path, 'PNG')

    print(f"  Base map saved: {output_path}")

    return str(output_path)
