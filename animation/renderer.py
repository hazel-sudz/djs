"""
GPU-accelerated renderer using macOS Quartz/CoreGraphics.

Features:
- Pollution circles (size + color)
- Wind direction arrows from each sensor
"""

import math
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time

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
    """Simple GPU-accelerated frame renderer with wind vectors."""

    HEADER_HEIGHT = 90
    FOOTER_HEIGHT = 40
    LEFT_MARGIN = 30
    RIGHT_MARGIN = 180

    # Normalization ranges (based on data analysis)
    # Pollution: P1=2K, P99=194K - use 2K-150K for visualization
    POLLUTION_VIS_MIN = 2000
    POLLUTION_VIS_MAX = 150000

    # Wind speed: P1=0.04, P99=3.93 - use 0-4 m/s
    WIND_SPEED_MAX = 4.0

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

    def __init__(self, width: int, height: int, map_extent, pollution_min: float, pollution_max: float):
        self.width = width
        self.height = height
        self.map_extent = map_extent
        self.pollution_min = pollution_min
        self.pollution_max = pollution_max
        self.color_space = CGColorSpaceCreateDeviceRGB()
        self.base_map_image = None

        self.map_x = self.LEFT_MARGIN
        self.map_y = self.FOOTER_HEIGHT
        self.map_width = width - self.LEFT_MARGIN - self.RIGHT_MARGIN
        self.map_height = height - self.HEADER_HEIGHT - self.FOOTER_HEIGHT

        print(f"Renderer initialized")
        print(f"  Resolution: {width}x{height}")
        print(f"  Map area: {self.map_width}x{self.map_height}")

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

    def geo_to_pixel(self, lon: float, lat: float) -> tuple:
        """Convert geographic coordinates to pixel coordinates."""
        x_ratio = (lon - self.map_extent.lon_min) / (self.map_extent.lon_max - self.map_extent.lon_min)
        y_ratio = (lat - self.map_extent.lat_min) / (self.map_extent.lat_max - self.map_extent.lat_min)
        px = self.map_x + x_ratio * self.map_width
        # Invert y since image has y=0 at top but lat increases northward
        py = self.map_y + self.map_height - y_ratio * self.map_height
        return (px, py)

    def get_plasma_color(self, pollution: float) -> tuple:
        """Get plasma colormap color for pollution value (normalized to visual range)."""
        # Normalize to visual range for consistent coloring
        norm = (pollution - self.POLLUTION_VIS_MIN) / (self.POLLUTION_VIS_MAX - self.POLLUTION_VIS_MIN)
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
        norm = (pollution - self.POLLUTION_VIS_MIN) / (self.POLLUTION_VIS_MAX - self.POLLUTION_VIS_MIN)
        norm = max(0, min(1, norm))
        return 80 + norm * 120  # 80-200 pixels (bigger circles)

    def draw_label(self, ctx, text: str, x: float, y: float, font_size: float = 12,
                   bold: bool = True, bg_color=None, padding: float = 4, centered: bool = True):
        """Draw text label with optional background."""
        from CoreText import CTFontCreateWithName, CTLineCreateWithAttributedString, CTLineDraw, CTLineGetBoundsWithOptions, kCTFontAttributeName, kCTForegroundColorFromContextAttributeName
        from Foundation import NSAttributedString
        from Quartz import CGContextSetTextMatrix, CGAffineTransformMake

        font_name = "Helvetica-Bold" if bold else "Helvetica"
        font = CTFontCreateWithName(font_name, font_size, None)
        attrs = {kCTFontAttributeName: font, kCTForegroundColorFromContextAttributeName: True}
        attr_string = NSAttributedString.alloc().initWithString_attributes_(text, attrs)
        line = CTLineCreateWithAttributedString(attr_string)
        bounds = CTLineGetBoundsWithOptions(line, 0)

        if centered:
            text_x = x - bounds.size.width / 2
        else:
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
        """Draw title with date and time."""
        title_y = self.height - 35
        self.draw_label(ctx, "Ultrafine Particle Pollution (UFP)", self.width / 2, title_y,
                        font_size=22, bold=True, centered=True)
        self.draw_label(ctx, f"{date_label}  •  {time_label}", self.width / 2, title_y - 28,
                        font_size=16, bold=False, centered=True)

    def draw_legend(self, ctx):
        """Draw color scale legend."""
        legend_x = self.width - self.RIGHT_MARGIN + 25
        legend_y = self.FOOTER_HEIGHT + 80
        bar_width = 25
        bar_height = 220

        # Draw gradient bar using visual range
        num_steps = 50
        step_height = bar_height / num_steps
        for i in range(num_steps):
            t = i / (num_steps - 1)
            pollution = self.POLLUTION_VIS_MIN + t * (self.POLLUTION_VIS_MAX - self.POLLUTION_VIS_MIN)
            color = self.get_plasma_color(pollution)
            CGContextSetFillColorWithColor(ctx, self.create_color(*color))
            CGContextFillRect(ctx, CGRectMake(legend_x, legend_y + i * step_height, bar_width, step_height + 1))

        # Border
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.3, 0.3, 0.3))
        CGContextSetLineWidth(ctx, 1)
        CGContextAddRect(ctx, CGRectMake(legend_x, legend_y, bar_width, bar_height))
        CGContextStrokePath(ctx)

        # Labels - use visual range with more tick marks
        tick_values = [2000, 25000, 50000, 75000, 100000, 125000, 150000]
        for val in tick_values:
            t = (val - self.POLLUTION_VIS_MIN) / (self.POLLUTION_VIS_MAX - self.POLLUTION_VIS_MIN)
            y_pos = legend_y + t * bar_height - 4
            text = f"{val/1000:.0f}K"
            self.draw_label(ctx, text, legend_x + bar_width + 8, y_pos, font_size=10, bold=False, centered=False)

        # Title
        self.draw_label(ctx, "Concentration", legend_x + bar_width / 2, legend_y + bar_height + 25,
                        font_size=10, bold=True, centered=True)
        self.draw_label(ctx, "(particles/cm³)", legend_x + bar_width / 2, legend_y + bar_height + 10,
                        font_size=9, bold=False, centered=True)

        # Wind legend
        wind_y = legend_y - 60
        self.draw_label(ctx, "Wind Direction", legend_x + bar_width / 2, wind_y,
                        font_size=10, bold=True, centered=True)
        # Draw sample arrow
        arrow_x = legend_x + bar_width / 2
        arrow_y = wind_y - 30
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.15, 0.35, 0.75, 0.8))
        CGContextSetLineWidth(ctx, 3)
        CGContextSetLineCap(ctx, kCGLineCapRound)
        CGContextMoveToPoint(ctx, arrow_x, arrow_y)
        CGContextAddLineToPoint(ctx, arrow_x + 35, arrow_y)
        CGContextStrokePath(ctx)
        # Arrowhead
        CGContextMoveToPoint(ctx, arrow_x + 28, arrow_y - 5)
        CGContextAddLineToPoint(ctx, arrow_x + 35, arrow_y)
        CGContextAddLineToPoint(ctx, arrow_x + 28, arrow_y + 5)
        CGContextStrokePath(ctx)

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
        norm_speed = min(1, max(0, wind_speed / self.WIND_SPEED_MAX))
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
        CGContextSetLineWidth(ctx, 2)
        CGContextSetLineJoin(ctx, kCGLineJoinRound)
        CGContextBeginPath(ctx)
        CGContextMoveToPoint(ctx, base1_x, base1_y)
        CGContextAddLineToPoint(ctx, tip_x, tip_y)
        CGContextAddLineToPoint(ctx, base2_x, base2_y)
        CGContextClosePath(ctx)
        CGContextStrokePath(ctx)

    def draw_average_wind(self, ctx, sensors):
        """Draw average wind indicator in center of map."""
        if not sensors:
            return

        # Calculate vector average of wind directions
        u_sum, v_sum, speed_sum = 0, 0, 0
        count = 0
        for sensor in sensors:
            lon, lat, pollution, wind_dir, wind_speed = sensor
            if wind_speed > 0.1:
                # Convert to radians (meteorological: 0=N, 90=E)
                rad = math.radians(wind_dir)
                u_sum += wind_speed * math.sin(rad)
                v_sum += wind_speed * math.cos(rad)
                speed_sum += wind_speed
                count += 1

        if count == 0:
            return

        # Average direction (where wind comes FROM)
        avg_dir = math.degrees(math.atan2(u_sum, v_sum)) % 360
        avg_speed = speed_sum / count

        # Center of map
        center_x = self.map_x + self.map_width / 2
        center_y = self.map_y + self.map_height / 2

        # Draw background circle
        bg_radius = 45
        CGContextSetFillColorWithColor(ctx, self.create_color(1, 1, 1, 0.85))
        CGContextAddEllipseInRect(ctx, CGRectMake(center_x - bg_radius, center_y - bg_radius,
                                                   bg_radius * 2, bg_radius * 2))
        CGContextFillPath(ctx)
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.3, 0.3, 0.3, 0.8))
        CGContextSetLineWidth(ctx, 2)
        CGContextAddEllipseInRect(ctx, CGRectMake(center_x - bg_radius, center_y - bg_radius,
                                                   bg_radius * 2, bg_radius * 2))
        CGContextStrokePath(ctx)

        # Draw wind arrow from center
        self.draw_wind_arrow(ctx, center_x, center_y, avg_dir, avg_speed, bg_radius)

        # Label
        self.draw_label(ctx, "Avg Wind", center_x, center_y + bg_radius + 16,
                       font_size=10, bold=True, bg_color=self.create_color(1, 1, 1, 0.85))

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

        # Draw sensor circles first
        for sensor in frame.sensors:
            lon, lat, pollution, wind_dir, wind_speed = sensor
            pos = self.geo_to_pixel(lon, lat)
            size = self.get_circle_size(pollution)
            color = self.get_plasma_color(pollution)

            # Main circle
            CGContextSetFillColorWithColor(ctx, self.create_color(*color, 0.9))
            CGContextAddEllipseInRect(ctx, CGRectMake(pos[0] - size/2, pos[1] - size/2, size, size))
            CGContextFillPath(ctx)

            # Circle border
            CGContextSetStrokeColorWithColor(ctx, self.create_color(*color, 1.0))
            CGContextSetLineWidth(ctx, 2.5)
            CGContextAddEllipseInRect(ctx, CGRectMake(pos[0] - size/2, pos[1] - size/2, size, size))
            CGContextStrokePath(ctx)

        # Draw wind arrows on top (starting from edge of circles)
        for sensor in frame.sensors:
            lon, lat, pollution, wind_dir, wind_speed = sensor
            pos = self.geo_to_pixel(lon, lat)
            circle_size = self.get_circle_size(pollution)
            self.draw_wind_arrow(ctx, pos[0], pos[1], wind_dir, wind_speed, circle_size / 2)

        # Draw pollution labels on top
        for sensor in frame.sensors:
            lon, lat, pollution, wind_dir, wind_speed = sensor
            pos = self.geo_to_pixel(lon, lat)
            size = self.get_circle_size(pollution)
            label = f"{pollution/1000:.1f}K" if pollution >= 1000 else f"{pollution:.0f}"
            self.draw_label(ctx, label, pos[0], pos[1] + size/2 + 14,
                           font_size=10, bold=True, bg_color=self.create_color(1, 1, 1, 0.85))

        # Draw average wind indicator in center
        self.draw_average_wind(ctx, frame.sensors)

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
