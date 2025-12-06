"""
GPU-accelerated renderer using macOS Quartz/CoreGraphics.

Features:
- Pollution circles (size + color)
- Wind direction arrows from each sensor
- Multi-site and multi-pollution type support
"""

import math
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from site_config import SiteConfig, PollutionType

import Quartz
from Quartz import (
    CGColorSpaceCreateDeviceRGB,
    CGBitmapContextCreate,
    CGBitmapContextCreateImage,
    CGContextSetFillColorWithColor,
    CGContextFillRect,
    CGContextSetStrokeColorWithColor,
    CGContextSetLineWidth,
    CGContextSetLineCap,
    CGContextSetLineJoin,
    CGContextBeginPath,
    CGContextClosePath,
    CGContextMoveToPoint,
    CGContextAddLineToPoint,
    CGContextStrokePath,
    CGContextAddEllipseInRect,
    CGContextFillPath,
    CGContextAddRect,
    CGContextDrawImage,
    CGContextSaveGState,
    CGContextRestoreGState,
    CGContextSetAllowsAntialiasing,
    CGContextSetShouldAntialias,
    CGContextSetInterpolationQuality,
    CGContextClip,
    CGImageDestinationCreateWithURL,
    CGImageDestinationAddImage,
    CGImageDestinationFinalize,
    kCGLineCapRound,
    kCGLineJoinRound,
    kCGInterpolationHigh,
    CGColorCreate,
    CGRectMake,
)
import CoreFoundation
from Foundation import NSURL
from PIL import Image
import numpy as np


class Renderer:
    """GPU-accelerated frame renderer with wind vectors and multi-site support."""

    HEADER_HEIGHT = 144
    FOOTER_HEIGHT = 64
    LEFT_MARGIN = 88
    RIGHT_MARGIN = 288

    # Plasma colormap
    PLASMA_COLORS = [
        (0.050, 0.030, 0.528), (0.133, 0.022, 0.563), (0.208, 0.020, 0.588),
        (0.282, 0.024, 0.602), (0.352, 0.034, 0.607), (0.417, 0.050, 0.601),
        (0.478, 0.071, 0.586), (0.536, 0.095, 0.563), (0.591, 0.121, 0.533),
        (0.643, 0.150, 0.498), (0.692, 0.180, 0.459), (0.738, 0.213, 0.418),
        (0.781, 0.248, 0.375), (0.821, 0.286, 0.332), (0.857, 0.326, 0.289),
        (0.890, 0.369, 0.246), (0.918, 0.416, 0.204), (0.942, 0.466, 0.163),
        (0.960, 0.520, 0.124), (0.973, 0.578, 0.089), (0.981, 0.639, 0.058),
        (0.984, 0.702, 0.038), (0.981, 0.768, 0.034), (0.972, 0.834, 0.053),
        (0.959, 0.899, 0.101), (0.940, 0.975, 0.131),
    ]

    def __init__(self, width: int, height: int, site_config: 'SiteConfig',
                 pollution_type: 'PollutionType'):
        """
        Initialize renderer with site and pollution type configuration.

        Args:
            width: Frame width in pixels
            height: Frame height in pixels
            site_config: Site configuration object
            pollution_type: Pollution type configuration
        """
        self.width = width
        self.height = height
        self.site_config = site_config
        self.pollution_type = pollution_type
        self.map_extent = site_config.get_map_extent()

        # Visualization ranges from config
        self.pollution_vis_min = pollution_type.vis_min
        self.pollution_vis_max = pollution_type.vis_max
        self.wind_speed_max = site_config.wind_speed_max

        # Circle sizing from config
        self.circle_min = site_config.circle_min
        self.circle_max = site_config.circle_max

        self.color_space = CGColorSpaceCreateDeviceRGB()
        self.base_map_image = None

        self.map_x = self.LEFT_MARGIN
        self.map_y = self.FOOTER_HEIGHT
        self.map_width = width - self.LEFT_MARGIN - self.RIGHT_MARGIN
        self.map_height = height - self.HEADER_HEIGHT - self.FOOTER_HEIGHT

        print(f"Renderer initialized for {site_config.display_name} - {pollution_type.display_name}")
        print(f"  Resolution: {width}x{height}")
        print(f"  Map area: {self.map_width}x{self.map_height}")
        print(f"  Pollution range: {self.pollution_vis_min} - {self.pollution_vis_max} {pollution_type.unit}")

    def load_base_map(self, path: str):
        """Load pre-rendered base map image."""
        pil_image = Image.open(path).convert('RGBA')
        pil_image = pil_image.resize((self.map_width, self.map_height), Image.LANCZOS)

        data = pil_image.tobytes()
        provider = Quartz.CGDataProviderCreateWithData(None, data, len(data), None)
        self.base_map_image = Quartz.CGImageCreate(
            self.map_width, self.map_height, 8, 32, self.map_width * 4,
            self.color_space, Quartz.kCGImageAlphaPremultipliedLast,
            provider, None, True, Quartz.kCGRenderingIntentDefault
        )
        # Keep reference to prevent garbage collection
        self._base_map_data = data
        print(f"  Base map loaded: {path}")

    def create_color(self, r: float, g: float, b: float, a: float = 1.0):
        """Create a CGColor."""
        return CGColorCreate(self.color_space, [r, g, b, a])

    def lat_to_mercator(self, lat: float) -> float:
        """Convert latitude to Mercator Y value (normalized)."""
        lat_rad = math.radians(lat)
        return math.asinh(math.tan(lat_rad)) / math.pi

    def geo_to_pixel(self, lon: float, lat: float) -> tuple:
        """Convert geographic coordinates to pixel coordinates using Mercator projection."""
        # Longitude is linear
        x_ratio = (lon - self.map_extent.lon_min) / (self.map_extent.lon_max - self.map_extent.lon_min)

        # Latitude uses Mercator projection
        merc_lat = self.lat_to_mercator(lat)
        merc_lat_min = self.lat_to_mercator(self.map_extent.lat_min)
        merc_lat_max = self.lat_to_mercator(self.map_extent.lat_max)
        y_ratio = (merc_lat - merc_lat_min) / (merc_lat_max - merc_lat_min)

        px = self.map_x + x_ratio * self.map_width
        # Higher latitude = higher y_ratio = higher on map (higher y in Quartz)
        py = self.map_y + y_ratio * self.map_height
        return (px, py)

    def get_plasma_color(self, pollution: float) -> tuple:
        """Get plasma colormap color for pollution value (normalized to visual range)."""
        # Normalize to visual range for consistent coloring
        norm = (pollution - self.pollution_vis_min) / (self.pollution_vis_max - self.pollution_vis_min)
        norm = max(0, min(1, norm))
        idx = norm * (len(self.PLASMA_COLORS) - 1)
        i = int(idx)
        f = idx - i
        if i >= len(self.PLASMA_COLORS) - 1:
            return self.PLASMA_COLORS[-1]
        c1, c2 = self.PLASMA_COLORS[i], self.PLASMA_COLORS[i + 1]
        return tuple(c1[j] + f * (c2[j] - c1[j]) for j in range(3))

    def get_circle_size(self, pollution: float) -> float:
        """Get circle size based on pollution level (normalized to visual range)."""
        # Normalize to visual range, not data range
        norm = (pollution - self.pollution_vis_min) / (self.pollution_vis_max - self.pollution_vis_min)
        norm = max(0, min(1, norm))
        size_range = self.circle_max - self.circle_min
        return self.circle_min + norm * size_range

    def draw_label(self, ctx, text: str, x: float, y: float, font_size: float = 12,
                   bold: bool = True, bg_color=None, padding: float = 4, anchor: str = "center"):
        """Draw text label with optional background.

        Args:
            anchor: Text alignment - "left", "center", or "right"
        """
        from CoreText import CTFontCreateWithName, CTLineCreateWithAttributedString, CTLineDraw, CTLineGetBoundsWithOptions, kCTFontAttributeName, kCTForegroundColorFromContextAttributeName
        from Foundation import NSAttributedString
        from Quartz import CGContextSetTextMatrix, CGAffineTransformMake

        font_name = "Helvetica-Bold" if bold else "Helvetica"
        font = CTFontCreateWithName(font_name, font_size, None)
        attrs = {kCTFontAttributeName: font, kCTForegroundColorFromContextAttributeName: True}
        attr_string = NSAttributedString.alloc().initWithString_attributes_(text, attrs)
        line = CTLineCreateWithAttributedString(attr_string)
        bounds = CTLineGetBoundsWithOptions(line, 0)

        if anchor == "center":
            text_x = x - bounds.size.width / 2
        elif anchor == "right":
            text_x = x - bounds.size.width
        else:  # left
            text_x = x

        text_y = y

        if bg_color:
            rect_w = bounds.size.width + padding * 2
            rect_h = bounds.size.height + padding * 2
            rect_x = text_x - padding
            rect_y = text_y - padding

            CGContextSetFillColorWithColor(ctx, bg_color)
            CGContextFillRect(ctx, CGRectMake(rect_x, rect_y, rect_w, rect_h))

        CGContextSetFillColorWithColor(ctx, self.create_color(0.15, 0.15, 0.15))
        CGContextSaveGState(ctx)
        CGContextSetTextMatrix(ctx, CGAffineTransformMake(1.0, 0.0, 0.0, 1.0, text_x, text_y))
        CTLineDraw(line, ctx)
        CGContextRestoreGState(ctx)

    def draw_title(self, ctx, date_label: str, time_label: str):
        """Draw title with site name, pollution type, date and time."""
        title_y = self.height - 56  # More margin from top
        # Include site name in title
        title_text = f"{self.site_config.display_name} — {self.pollution_type.display_name} — {self.pollution_type.unit}"
        self.draw_label(ctx, title_text, self.width / 2, title_y,
                        font_size=32, bold=True, anchor="center")
        self.draw_label(ctx, f"{date_label}  •  {time_label}", self.width / 2, title_y - 28,
                        font_size=26, bold=False, anchor="center")

    def draw_legend(self, ctx):
        """Draw color scale legend, centered in the right margin."""
        bar_width = 25
        bar_height = 410  # 75% taller than original
        # Center legend horizontally in the right margin (accounting for labels on right side)
        margin_center_x = self.width - self.RIGHT_MARGIN / 2
        legend_x = margin_center_x - bar_width / 2 - 15  # Offset left to account for right-side labels
        # Center legend vertically in the map area
        map_center_y = self.map_y + self.map_height / 2
        legend_y = map_center_y - bar_height / 2

        # Draw gradient bar using visual range
        num_steps = 50
        step_height = bar_height / num_steps
        for i in range(num_steps):
            t = i / (num_steps - 1)
            pollution = self.pollution_vis_min + t * (self.pollution_vis_max - self.pollution_vis_min)
            color = self.get_plasma_color(pollution)
            CGContextSetFillColorWithColor(ctx, self.create_color(*color))
            CGContextFillRect(ctx, CGRectMake(legend_x, legend_y + i * step_height, bar_width, step_height + 1))

        # Border
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.3, 0.3, 0.3))
        CGContextSetLineWidth(ctx, 1)
        CGContextAddRect(ctx, CGRectMake(legend_x, legend_y, bar_width, bar_height))
        CGContextStrokePath(ctx)

        # Generate tick values based on pollution range
        vis_range = self.pollution_vis_max - self.pollution_vis_min
        num_ticks = 5
        tick_values = [self.pollution_vis_min + i * vis_range / (num_ticks - 1) for i in range(num_ticks)]

        for val in tick_values:
            t = (val - self.pollution_vis_min) / (self.pollution_vis_max - self.pollution_vis_min)
            y_pos = legend_y + t * bar_height - 6
            # Format based on magnitude
            if val >= 1000:
                text = f"{val/1000:.0f}K"
            else:
                text = f"{val:.0f}"
            self.draw_label(ctx, text, legend_x + bar_width + 24, y_pos, font_size=23, bold=False, anchor="left")

        # Title
        self.draw_label(ctx, "Concentration", legend_x + bar_width / 2, legend_y + bar_height + 72,
                        font_size=26, bold=True, anchor="center")
        self.draw_label(ctx, f"({self.pollution_type.unit})", legend_x + bar_width / 2, legend_y + bar_height + 35,
                        font_size=23, bold=False, anchor="center")

    def draw_region_overlays(self, ctx):
        """Draw region outlines and labels (Galena Park boundary, Ship Channel label, etc.)."""
        # Only draw for ECAGP site
        if self.site_config.name != "ecagp":
            return

        # Set clipping rectangle to map bounds so overlays don't draw outside
        CGContextSaveGState(ctx)
        CGContextBeginPath(ctx)
        CGContextAddRect(ctx, CGRectMake(self.map_x, self.map_y, self.map_width, self.map_height))
        CGContextClip(ctx)

        # Galena Park boundary - exact coordinates from OpenStreetMap
        galena_park_boundary = [
            (-95.2517032, 29.7598861),
            (-95.2517823, 29.7576073),
            (-95.25429, 29.7575565),
            (-95.2542305, 29.7554897),
            (-95.2541865, 29.7539748),
            (-95.2541239, 29.7516412),
            (-95.2540499, 29.7488888),
            (-95.2539794, 29.746568),
            (-95.253912, 29.7438133),
            (-95.253868, 29.7423128),
            (-95.253814, 29.7406654),
            (-95.2537783, 29.7392898),
            (-95.2537501, 29.7381756),
            (-95.2537156, 29.7368188),
            (-95.2536511, 29.734074),
            (-95.2530589, 29.7319111),
            (-95.2511484, 29.7320686),
            (-95.2486044, 29.730906),
            (-95.2462417, 29.72904),
            (-95.2436713, 29.7265721),
            (-95.2397213, 29.7281408),
            (-95.2377438, 29.729271),
            (-95.2342782, 29.7307764),
            (-95.2316619, 29.7316009),
            (-95.2294007, 29.7319424),
            (-95.2247865, 29.7324079),
            (-95.2225625, 29.7322554),
            (-95.2197107, 29.7315873),
            (-95.2184667, 29.7313177),
            (-95.2173781, 29.7315032),
            (-95.2127631, 29.7381002),
            (-95.2110485, 29.7413623),
            (-95.2114188, 29.7503271),
            (-95.2140964, 29.7594558),
            (-95.2146126, 29.7593),
            (-95.2159223, 29.7595134),
            (-95.2178387, 29.7594936),
            (-95.2269812, 29.7594221),
            (-95.2298431, 29.7593847),
            (-95.2320048, 29.7593426),
            (-95.2342269, 29.7593146),
            (-95.2380267, 29.759266),
            (-95.2420682, 29.7599636),
            (-95.2517032, 29.7598861),
        ]

        # Draw Galena Park boundary as solid line
        CGContextSaveGState(ctx)
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.8, 0.2, 0.3, 0.8))
        CGContextSetLineWidth(ctx, 4)

        CGContextBeginPath(ctx)
        first = True
        for lon, lat in galena_park_boundary:
            px, py = self.geo_to_pixel(lon, lat)
            if first:
                CGContextMoveToPoint(ctx, px, py)
                first = False
            else:
                CGContextAddLineToPoint(ctx, px, py)
        CGContextClosePath(ctx)
        CGContextStrokePath(ctx)
        CGContextRestoreGState(ctx)

        # Galena Park label - positioned above the outline
        gp_label_pos = self.geo_to_pixel(-95.230, 29.763)
        self.draw_label(ctx, "Galena Park", gp_label_pos[0], gp_label_pos[1],
                       font_size=29, bold=True, bg_color=self.create_color(1, 1, 1, 0.85))

        # Buffalo Bayou / Houston Ship Channel path - exact coordinates from OSM
        ship_channel_path = [
            (-95.3197549, 29.7559644),
            (-95.3173258, 29.7548765),
            (-95.3144591, 29.755264),
            (-95.3079992, 29.7545072),
            (-95.3042655, 29.7556621),
            (-95.300357, 29.7527144),
            (-95.2974163, 29.7542315),
            (-95.2962578, 29.7528751),
            (-95.294876, 29.75134),
            (-95.2887282, 29.7498828),
            (-95.2795981, 29.7384403),
            (-95.2714485, 29.7252607),
            (-95.2589619, 29.7272664),
            (-95.2491802, 29.721449),
            (-95.2418615, 29.719184),
            (-95.2292155, 29.725196),
            (-95.220332, 29.7246966),
            (-95.2096912, 29.7279764),
            (-95.2006925, 29.7406783),
            (-95.173454, 29.7470126),
            (-95.1592034, 29.7417418),
            (-95.1541154, 29.7372003),
            (-95.1400197, 29.7354902),
        ]

        # Draw ship channel path as solid blue line
        CGContextSaveGState(ctx)
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.2, 0.5, 0.9, 0.7))
        CGContextSetLineWidth(ctx, 4)

        CGContextBeginPath(ctx)
        first = True
        for lon, lat in ship_channel_path:
            px, py = self.geo_to_pixel(lon, lat)
            if first:
                CGContextMoveToPoint(ctx, px, py)
                first = False
            else:
                CGContextAddLineToPoint(ctx, px, py)
        CGContextStrokePath(ctx)
        CGContextRestoreGState(ctx)

        # Houston Ship Channel label - on the waterway
        ship_channel_pos = self.geo_to_pixel(-95.185, 29.748)
        self.draw_label(ctx, "Houston Ship Channel", ship_channel_pos[0], ship_channel_pos[1],
                       font_size=22, bold=True, bg_color=self.create_color(0.85, 0.95, 1.0, 0.9))

        # Refineries and chemical plants near Galena Park - from OpenStreetMap
        refineries = [
            # Major refineries
            ("Valero Houston Refinery", -95.2524637, 29.7148001),
            ("LyondellBasell Refinery", -95.235027, 29.713241),
            ("PEMEX Deer Park", -95.1309608, 29.7234371),
            # Chemical plants
            ("Chevron Phillips", -95.181899, 29.735699),
            ("INEOS", -95.155457, 29.729319),
            ("BASF", -95.150252, 29.727939),
            ("Albemarle", -95.1695986, 29.7354737),
            ("Arkema", -95.1761636, 29.7591208),
            ("Sasol", -95.1777914, 29.7607649),
        ]

        # Draw refinery markers and labels
        for name, lon, lat in refineries:
            # Check if within map bounds
            if not (self.map_extent.lon_min <= lon <= self.map_extent.lon_max and
                    self.map_extent.lat_min <= lat <= self.map_extent.lat_max):
                continue

            px, py = self.geo_to_pixel(lon, lat)

            # Draw factory/refinery symbol (smokestack icon) - scaled for 2880x1920
            # Base rectangle
            CGContextSetFillColorWithColor(ctx, self.create_color(0.3, 0.3, 0.3, 0.9))
            CGContextFillRect(ctx, CGRectMake(px - 13, py - 10, 26, 20))
            # Smokestack
            CGContextFillRect(ctx, CGRectMake(px - 5, py + 10, 10, 16))
            # Smoke puff (circle)
            CGContextSetFillColorWithColor(ctx, self.create_color(0.5, 0.5, 0.5, 0.7))
            CGContextAddEllipseInRect(ctx, CGRectMake(px - 8, py + 24, 16, 13))
            CGContextFillPath(ctx)

            # Label
            self.draw_label(ctx, name, px, py - 30,
                           font_size=18, bold=True, bg_color=self.create_color(1, 0.95, 0.85, 0.9))

        # Restore state to remove clipping
        CGContextRestoreGState(ctx)

    def draw_coord_labels(self, ctx):
        """Draw lat/lon labels on the map edges."""
        # Get coordinate ranges from config
        (lon_start, lon_end), (lat_start, lat_end) = self.site_config.get_coord_label_ranges()
        step = self.site_config.coord_label_step

        # Draw longitude labels (at bottom)
        # Skip first label to avoid overlap with latitude labels in bottom-left corner
        # Skip last label to avoid running off the right edge
        lon = lon_start + step
        while lon < lon_end - step / 2:  # Stop before the last label
            p1 = self.geo_to_pixel(lon, self.map_extent.lat_min)
            self.draw_label(ctx, f"{lon:.2f}", p1[0], p1[1] - 19,
                           font_size=23, bold=True, bg_color=self.create_color(1, 1, 1, 0.9))
            lon += step

        # Draw latitude labels (at left edge, half on border like longitude labels)
        # Use smaller step for latitude to get more labels (vertical range is usually smaller)
        lat_step = step / 2  # 0.01 instead of 0.02
        # Skip first label to match the skipped longitude label in corner
        lat = lat_start + lat_step
        while lat <= lat_end + lat_step / 2:  # Small tolerance for floating point
            p1 = self.geo_to_pixel(self.map_extent.lon_min, lat)
            # Skip if label would be too close to top or bottom edge of frame
            if p1[1] < 30 or p1[1] > self.height - 30:
                lat += lat_step
                continue
            # Position label so right edge is at map border (half on, half outside)
            self.draw_label(ctx, f"{lat:.2f}", p1[0], p1[1] - 8,
                           font_size=23, bold=True, bg_color=self.create_color(1, 1, 1, 0.9),
                           anchor="right")
            lat += lat_step

    def draw_wind_arrow(self, ctx, x: float, y: float, wind_dir: float, wind_speed: float, circle_radius: float = 0):
        """
        Draw wind as a clean cone starting from edge of pollution circle.
        """
        if wind_speed < 0.1:
            return

        # Convert meteorological direction to angle
        to_dir = (wind_dir + 180) % 360
        angle_rad = math.radians(90 - to_dir)

        # Cone dimensions based on wind speed
        norm_speed = min(1, max(0, wind_speed / self.wind_speed_max))
        cone_length = 80 + norm_speed * 60  # 80-140px (shorter, cleaner)
        base_width = 16 + norm_speed * 8  # 16-24px at base

        # Start from edge of circle (with small gap)
        gap = 8
        start_x = x + (circle_radius + gap) * math.cos(angle_rad)
        start_y = y + (circle_radius + gap) * math.sin(angle_rad)

        # Calculate tip position
        tip_x = start_x + cone_length * math.cos(angle_rad)
        tip_y = start_y + cone_length * math.sin(angle_rad)

        # Perpendicular for base width
        perp_angle = angle_rad + math.pi / 2

        # Base corners
        base1_x = start_x + (base_width / 2) * math.cos(perp_angle)
        base1_y = start_y + (base_width / 2) * math.sin(perp_angle)
        base2_x = start_x - (base_width / 2) * math.cos(perp_angle)
        base2_y = start_y - (base_width / 2) * math.sin(perp_angle)

        # === Subtle Drop Shadow ===
        shadow_offset = 3
        shadow_color = self.create_color(0, 0, 0, 0.2)
        CGContextSetFillColorWithColor(ctx, shadow_color)
        CGContextBeginPath(ctx)
        CGContextMoveToPoint(ctx, base1_x + shadow_offset, base1_y - shadow_offset)
        CGContextAddLineToPoint(ctx, tip_x + shadow_offset, tip_y - shadow_offset)
        CGContextAddLineToPoint(ctx, base2_x + shadow_offset, base2_y - shadow_offset)
        CGContextClosePath(ctx)
        CGContextFillPath(ctx)

        # === Main Cone - solid clean fill ===
        cone_color = self.create_color(0.2, 0.4, 0.7, 0.85)
        CGContextSetFillColorWithColor(ctx, cone_color)
        CGContextBeginPath(ctx)
        CGContextMoveToPoint(ctx, base1_x, base1_y)
        CGContextAddLineToPoint(ctx, tip_x, tip_y)
        CGContextAddLineToPoint(ctx, base2_x, base2_y)
        CGContextClosePath(ctx)
        CGContextFillPath(ctx)

        # === Clean white border ===
        border_color = self.create_color(1, 1, 1, 0.9)
        CGContextSetStrokeColorWithColor(ctx, border_color)
        CGContextSetLineWidth(ctx, 3)
        CGContextSetLineJoin(ctx, kCGLineJoinRound)
        CGContextBeginPath(ctx)
        CGContextMoveToPoint(ctx, base1_x, base1_y)
        CGContextAddLineToPoint(ctx, tip_x, tip_y)
        CGContextAddLineToPoint(ctx, base2_x, base2_y)
        CGContextClosePath(ctx)
        CGContextStrokePath(ctx)

    def draw_wind_indicator(self, ctx, sensors):
        """Draw wind indicator in center of map (from weather station data)."""
        if not sensors:
            return

        # Get wind from first sensor (all sensors have same station wind data)
        wind_dir = None
        wind_speed = None
        for sensor in sensors:
            lon, lat, pollution, wd, ws, sensor_id = sensor
            if not math.isnan(ws) if ws is not None else False:
                wind_speed = ws
                wind_dir = wd if (wd is not None and not math.isnan(wd)) else None
                break

        if wind_speed is None:
            return

        # Check if calm (very low wind)
        is_calm = wind_speed <= 0.1 or wind_dir is None

        # Center of map
        center_x = self.map_x + self.map_width / 2
        center_y = self.map_y + self.map_height / 2

        # Draw background circle
        bg_radius = 72
        CGContextSetFillColorWithColor(ctx, self.create_color(1, 1, 1, 0.85))
        CGContextAddEllipseInRect(ctx, CGRectMake(center_x - bg_radius, center_y - bg_radius,
                                                   bg_radius * 2, bg_radius * 2))
        CGContextFillPath(ctx)
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.3, 0.3, 0.3, 0.8))
        CGContextSetLineWidth(ctx, 3)
        CGContextAddEllipseInRect(ctx, CGRectMake(center_x - bg_radius, center_y - bg_radius,
                                                   bg_radius * 2, bg_radius * 2))
        CGContextStrokePath(ctx)

        # Draw wind arrow from center (if not calm)
        if not is_calm:
            self.draw_wind_arrow(ctx, center_x, center_y, wind_dir, wind_speed, bg_radius)

        # Wind speed label inside circle
        if is_calm:
            speed_label = "Calm"
        else:
            speed_label = f"{wind_speed:.1f} m/s"
        self.draw_label(ctx, speed_label, center_x, center_y - 8,
                       font_size=23, bold=True, bg_color=self.create_color(1, 1, 1, 0.9))

        # Label above circle
        self.draw_label(ctx, "Wind Speed", center_x, center_y + bg_radius + 32,
                       font_size=22, bold=True, bg_color=self.create_color(1, 1, 1, 0.85))
        # Station info below circle (from site config)
        station_name = self.site_config.wind_station_name
        station_lat, station_lon = self.site_config.wind_station_coords
        station_label = f"{station_name} ({station_lat:.2f}, {station_lon:.2f})"
        self.draw_label(ctx, station_label, center_x, center_y - bg_radius - 29,
                       font_size=16, bold=False, bg_color=self.create_color(1, 1, 1, 0.8))

    def render_frame(self, frame) -> bytes:
        """Render a single frame."""
        ctx = CGBitmapContextCreate(
            None, self.width, self.height, 8, self.width * 4,
            self.color_space, Quartz.kCGImageAlphaPremultipliedLast
        )

        CGContextSetAllowsAntialiasing(ctx, True)
        CGContextSetShouldAntialias(ctx, True)
        CGContextSetInterpolationQuality(ctx, kCGInterpolationHigh)

        # Background
        CGContextSetFillColorWithColor(ctx, self.create_color(0.97, 0.97, 0.97))
        CGContextFillRect(ctx, CGRectMake(0, 0, self.width, self.height))

        # Map border
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.75, 0.75, 0.75))
        CGContextSetLineWidth(ctx, 1)
        CGContextAddRect(ctx, CGRectMake(self.map_x, self.map_y, self.map_width, self.map_height))
        CGContextStrokePath(ctx)

        # Base map
        if self.base_map_image:
            CGContextDrawImage(ctx, CGRectMake(self.map_x, self.map_y, self.map_width, self.map_height),
                             self.base_map_image)

        # Draw region overlays (Galena Park boundary, labels)
        self.draw_region_overlays(ctx)

        # Draw coordinate labels
        self.draw_coord_labels(ctx)

        # Draw sensor circles first
        for sensor in frame.sensors:
            lon, lat, pollution, wind_dir, wind_speed, sensor_id = sensor
            pos = self.geo_to_pixel(lon, lat)

            # Check for missing data (NaN)
            is_na = math.isnan(pollution) if pollution is not None else True

            if is_na:
                # Use minimum size and gray color for NA
                size = self.circle_min
                color = (0.5, 0.5, 0.5)  # Gray
                alpha = 0.5
            else:
                size = self.get_circle_size(pollution)
                color = self.get_plasma_color(pollution)
                alpha = 0.9

            # Main circle
            CGContextSetFillColorWithColor(ctx, self.create_color(*color, alpha))
            CGContextAddEllipseInRect(ctx, CGRectMake(pos[0] - size/2, pos[1] - size/2, size, size))
            CGContextFillPath(ctx)

            # Circle border
            CGContextSetStrokeColorWithColor(ctx, self.create_color(*color, min(1.0, alpha + 0.1)))
            CGContextSetLineWidth(ctx, 4)
            CGContextAddEllipseInRect(ctx, CGRectMake(pos[0] - size/2, pos[1] - size/2, size, size))
            CGContextStrokePath(ctx)

        # Draw labels on circles - with offset for overlapping sensors
        sensor_positions = [(self.geo_to_pixel(s[0], s[1]), s) for s in frame.sensors]

        for i, (pos, sensor) in enumerate(sensor_positions):
            lon, lat, pollution, wind_dir, wind_speed, sensor_id = sensor

            # Check for missing data (NaN)
            is_na = math.isnan(pollution) if pollution is not None else True
            size = self.circle_min if is_na else self.get_circle_size(pollution)

            # Check if this sensor overlaps with others and calculate offset
            x_offset = 0
            y_offset = 0
            for j, (other_pos, other_sensor) in enumerate(sensor_positions):
                if i != j:
                    dist = math.sqrt((pos[0] - other_pos[0])**2 + (pos[1] - other_pos[1])**2)
                    if dist < 192:  # Sensors are close
                        # Offset labels horizontally based on relative position
                        if pos[0] < other_pos[0]:
                            x_offset = -96  # This sensor is to the left, offset label left
                        else:
                            x_offset = 96   # This sensor is to the right, offset label right

            # Sensor name and pollution value labels
            sensor_name = self.site_config.get_sensor_display_name(sensor_id)
            label_x = pos[0] + x_offset

            # Pollution value label (or "NA" if missing)
            if is_na:
                pollution_label = "NA"
            else:
                short_unit = self.pollution_type.unit.split('/')[0].replace('particles', 'p') + '/' + self.pollution_type.unit.split('/')[-1] if '/' in self.pollution_type.unit else self.pollution_type.unit
                if pollution >= 1000:
                    pollution_label = f"{pollution/1000:.1f}K {short_unit}"
                else:
                    pollution_label = f"{pollution:.0f} {short_unit}"

            # For Eastie: sensor name at bottom, pollution at top
            # For other sites: both labels above the circle
            if self.site_config.name == "eastie":
                # Pollution at top
                self.draw_label(ctx, pollution_label, label_x, pos[1] + size/2 + 40,
                               font_size=23, bold=True, bg_color=self.create_color(1, 1, 1, 0.85))
                # Sensor name at bottom
                self.draw_label(ctx, sensor_name, label_x, pos[1] - size/2 - 40,
                               font_size=23, bold=True, bg_color=self.create_color(1, 1, 1, 0.9))
            else:
                # Both above circle (sensor name closer, pollution further up)
                self.draw_label(ctx, sensor_name, label_x, pos[1] - size/2 - 29,
                               font_size=23, bold=True, bg_color=self.create_color(1, 1, 1, 0.9))
                self.draw_label(ctx, pollution_label, label_x, pos[1] - size/2 - 64,
                               font_size=23, bold=True, bg_color=self.create_color(1, 1, 1, 0.85))

        # Draw wind indicator in center (from weather station)
        self.draw_wind_indicator(ctx, frame.sensors)

        # Title
        self.draw_title(ctx, frame.date_label, frame.time_label)

        # Legend
        self.draw_legend(ctx)

        return CGBitmapContextCreateImage(ctx)

    def save_image(self, image, path: str):
        url = NSURL.fileURLWithPath_(path)
        dest = CGImageDestinationCreateWithURL(url, "public.png", 1, None)
        CGImageDestinationAddImage(dest, image, None)
        CGImageDestinationFinalize(dest)

    def render_all_frames(self, frames: list, output_dir: str, num_workers: int = 8, start_frame: int = 1) -> int:
        """
        Render all frames in parallel.

        Returns:
            Next frame number (for sequential numbering across days)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        total = len(frames)
        print(f"\nRendering {total} frames...")

        start_time = time.time()
        completed = [0]

        def render_one(args):
            i, frame = args
            image = self.render_frame(frame)
            frame_num = start_frame + i
            output_file = output_path / f"frame_{frame_num:05d}.png"
            self.save_image(image, str(output_file))
            completed[0] += 1
            progress = (completed[0] * 100) // total
            print(f"\rProgress: {progress}% ({completed[0]}/{total} frames)", end="", flush=True)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            list(executor.map(render_one, enumerate(frames)))

        elapsed = time.time() - start_time
        print(f"\n  Rendered in {elapsed:.1f}s ({total/elapsed:.1f} fps)")

        return start_frame + total
