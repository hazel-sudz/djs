"""
Clear, intuitive UFP visualization renderer.

Design principles:
1. LOG SCALE for pollution (data spans 3 orders of magnitude)
2. Air Quality Index style colors (green=good → red=bad → purple=hazardous)
3. Large, readable numeric values on each sensor
4. Single bold wind arrow with clear direction
5. Simple smoke plumes extending downwind
6. No confusing transport arrows or complex indicators
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
    CGContextMoveToPoint,
    CGContextAddLineToPoint,
    CGContextStrokePath,
    CGContextAddEllipseInRect,
    CGContextFillPath,
    CGContextSetLineCap,
    CGContextSetLineJoin,
    CGContextAddRect,
    CGContextDrawImage,
    CGContextSaveGState,
    CGContextRestoreGState,
    CGContextSetAllowsAntialiasing,
    CGContextSetShouldAntialias,
    CGContextSetInterpolationQuality,
    CGContextBeginPath,
    CGContextClosePath,
    CGImageDestinationCreateWithURL,
    CGImageDestinationAddImage,
    CGImageDestinationFinalize,
    kCGLineCapRound,
    kCGLineJoinRound,
    kCGInterpolationHigh,
    CGColorCreate,
    CGRectMake,
)
from Foundation import NSURL, NSAttributedString, NSDictionary
import CoreText
from PIL import Image
import numpy as np


class ClearRenderer:
    """Clear, intuitive pollution visualization."""

    HEADER_HEIGHT = 100
    FOOTER_HEIGHT = 40
    LEFT_MARGIN = 30
    RIGHT_MARGIN = 200  # Space for dashboard

    # Air Quality Index inspired colors (on log scale)
    # pollution_min (e.g., 1000) = green, pollution_max (e.g., 300000) = purple
    AQI_COLORS = [
        (0.2, 0.8, 0.3),    # Green - Good
        (0.6, 0.9, 0.2),    # Light green
        (0.95, 0.9, 0.2),   # Yellow - Moderate
        (1.0, 0.7, 0.1),    # Orange - Unhealthy for sensitive
        (1.0, 0.4, 0.1),    # Dark orange
        (0.9, 0.2, 0.2),    # Red - Unhealthy
        (0.7, 0.1, 0.3),    # Dark red - Very unhealthy
        (0.5, 0.0, 0.5),    # Purple - Hazardous
    ]

    def __init__(self, width: int, height: int, map_extent,
                 pollution_min: float = 1000, pollution_max: float = 300000):
        self.width = width
        self.height = height
        self.map_extent = map_extent

        # Use log scale for pollution
        self.pollution_min = max(pollution_min, 100)  # Avoid log(0)
        self.pollution_max = pollution_max
        self.log_min = math.log10(self.pollution_min)
        self.log_max = math.log10(self.pollution_max)

        self.color_space = CGColorSpaceCreateDeviceRGB()
        self.base_map_image = None
        self.base_map_data = None

        self.map_x = self.LEFT_MARGIN
        self.map_y = self.FOOTER_HEIGHT
        self.map_width = width - self.LEFT_MARGIN - self.RIGHT_MARGIN
        self.map_height = height - self.HEADER_HEIGHT - self.FOOTER_HEIGHT

        print(f"Clear Renderer: {width}x{height}, pollution log scale: {self.log_min:.1f} - {self.log_max:.1f}")

    def load_base_map(self, path: str):
        pil_image = Image.open(path).convert('RGBA')
        pil_image = pil_image.resize((self.map_width, self.map_height), Image.LANCZOS)
        img_array = np.array(pil_image)
        self.base_map_data = img_array.tobytes()
        provider = Quartz.CGDataProviderCreateWithData(None, self.base_map_data, len(self.base_map_data), None)
        self.base_map_image = Quartz.CGImageCreate(
            self.map_width, self.map_height, 8, 32, self.map_width * 4,
            self.color_space, Quartz.kCGImageAlphaPremultipliedLast,
            provider, None, True, Quartz.kCGRenderingIntentDefault
        )

    def geo_to_pixel(self, lon: float, lat: float) -> tuple:
        rel_x = (lon - self.map_extent.lon_min) / (self.map_extent.lon_max - self.map_extent.lon_min)
        rel_y = 1.0 - (lat - self.map_extent.lat_min) / (self.map_extent.lat_max - self.map_extent.lat_min)
        return (self.map_x + rel_x * self.map_width, self.map_y + rel_y * self.map_height)

    def get_log_normalized(self, value: float) -> float:
        """Convert pollution value to 0-1 on log scale."""
        if value <= 0:
            return 0
        log_val = math.log10(max(value, self.pollution_min))
        return max(0, min(1, (log_val - self.log_min) / (self.log_max - self.log_min)))

    def get_aqi_color(self, value: float) -> tuple:
        """Get AQI-style color for pollution value (log scale)."""
        normalized = self.get_log_normalized(value)

        # Map to color index
        index = normalized * (len(self.AQI_COLORS) - 1)
        lower_idx = int(index)
        upper_idx = min(lower_idx + 1, len(self.AQI_COLORS) - 1)
        fraction = index - lower_idx

        lower, upper = self.AQI_COLORS[lower_idx], self.AQI_COLORS[upper_idx]
        return (
            lower[0] + (upper[0] - lower[0]) * fraction,
            lower[1] + (upper[1] - lower[1]) * fraction,
            lower[2] + (upper[2] - lower[2]) * fraction
        )

    def get_circle_size(self, pollution: float) -> float:
        """Get circle size based on log-scaled pollution."""
        normalized = self.get_log_normalized(pollution)
        # Much larger range: 30 to 120 pixels
        return 30 + normalized * 90

    def create_color(self, r: float, g: float, b: float, a: float = 1.0):
        return CGColorCreate(self.color_space, [r, g, b, a])

    def draw_text(self, ctx, text: str, x: float, y: float, font_size: float = 12,
                  bold: bool = False, color: tuple = (0.1, 0.1, 0.1), center: bool = True):
        """Draw text at position."""
        font_name = "Helvetica-Bold" if bold else "Helvetica"
        font = CoreText.CTFontCreateWithName(font_name, font_size, None)
        attrs = NSDictionary.dictionaryWithObjects_forKeys_(
            [font, True],
            [CoreText.kCTFontAttributeName, CoreText.kCTForegroundColorFromContextAttributeName]
        )
        attr_string = NSAttributedString.alloc().initWithString_attributes_(text, attrs)
        line = CoreText.CTLineCreateWithAttributedString(attr_string)
        bounds = CoreText.CTLineGetBoundsWithOptions(line, 0)

        CGContextSetFillColorWithColor(ctx, self.create_color(*color))
        CGContextSaveGState(ctx)

        if center:
            tx = x - bounds.size.width / 2
        else:
            tx = x
        ty = y - bounds.size.height / 2

        Quartz.CGContextSetTextPosition(ctx, tx, ty)
        CoreText.CTLineDraw(line, ctx)
        CGContextRestoreGState(ctx)

        return bounds.size.width, bounds.size.height

    def draw_text_with_background(self, ctx, text: str, x: float, y: float,
                                   font_size: float = 12, bold: bool = True,
                                   text_color: tuple = (0.1, 0.1, 0.1),
                                   bg_color: tuple = (1, 1, 1, 0.9),
                                   padding: float = 6):
        """Draw text with background box."""
        font_name = "Helvetica-Bold" if bold else "Helvetica"
        font = CoreText.CTFontCreateWithName(font_name, font_size, None)
        attrs = NSDictionary.dictionaryWithObjects_forKeys_(
            [font, True],
            [CoreText.kCTFontAttributeName, CoreText.kCTForegroundColorFromContextAttributeName]
        )
        attr_string = NSAttributedString.alloc().initWithString_attributes_(text, attrs)
        line = CoreText.CTLineCreateWithAttributedString(attr_string)
        bounds = CoreText.CTLineGetBoundsWithOptions(line, 0)

        rect_w = bounds.size.width + padding * 2
        rect_h = bounds.size.height + padding * 2
        rect_x = x - rect_w / 2
        rect_y = y - rect_h / 2

        # Shadow
        CGContextSetFillColorWithColor(ctx, self.create_color(0, 0, 0, 0.15))
        CGContextFillRect(ctx, CGRectMake(rect_x + 2, rect_y - 2, rect_w, rect_h))

        # Background
        CGContextSetFillColorWithColor(ctx, self.create_color(*bg_color))
        CGContextFillRect(ctx, CGRectMake(rect_x, rect_y, rect_w, rect_h))

        # Border
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.5, 0.5, 0.5, 0.5))
        CGContextSetLineWidth(ctx, 0.5)
        CGContextAddRect(ctx, CGRectMake(rect_x, rect_y, rect_w, rect_h))
        CGContextStrokePath(ctx)

        # Text
        CGContextSetFillColorWithColor(ctx, self.create_color(*text_color))
        CGContextSaveGState(ctx)
        Quartz.CGContextSetTextPosition(ctx, rect_x + padding, rect_y + padding + 1)
        CoreText.CTLineDraw(line, ctx)
        CGContextRestoreGState(ctx)

    def draw_wind_arrow(self, ctx, wind_u: float, wind_v: float, wind_speed: float):
        """Draw a single, bold wind direction arrow at top of map."""
        # Position: top center of map
        cx = self.map_x + self.map_width / 2
        cy = self.map_y + self.map_height - 60

        # Check for calm wind
        if wind_speed < 0.3:
            # Draw "CALM" indicator
            CGContextSetFillColorWithColor(ctx, self.create_color(0.4, 0.6, 0.8, 0.9))
            CGContextAddEllipseInRect(ctx, CGRectMake(cx - 30, cy - 30, 60, 60))
            CGContextFillPath(ctx)
            CGContextSetStrokeColorWithColor(ctx, self.create_color(0.2, 0.4, 0.6, 0.9))
            CGContextSetLineWidth(ctx, 2)
            CGContextAddEllipseInRect(ctx, CGRectMake(cx - 30, cy - 30, 60, 60))
            CGContextStrokePath(ctx)
            self.draw_text(ctx, "CALM", cx, cy, font_size=14, bold=True, color=(1, 1, 1))
            return

        # Calculate wind direction (direction wind is blowing TO)
        wind_mag = math.sqrt(wind_u**2 + wind_v**2)
        if wind_mag < 0.01:
            return

        # Wind components: u=east, v=north
        # Arrow shows direction wind is BLOWING TO
        wu = wind_u / wind_mag   # Positive = east (right on screen)
        wv = wind_v / wind_mag   # Positive = north (up on screen)

        # Arrow length based on wind speed (30-80 pixels)
        arrow_len = 30 + min(wind_speed, 5) * 10

        # Arrow shaft
        start_x = cx - wu * arrow_len / 2
        start_y = cy - wv * arrow_len / 2
        end_x = cx + wu * arrow_len / 2
        end_y = cy + wv * arrow_len / 2

        # Draw arrow background (white glow)
        CGContextSetStrokeColorWithColor(ctx, self.create_color(1, 1, 1, 0.8))
        CGContextSetLineWidth(ctx, 12)
        CGContextSetLineCap(ctx, kCGLineCapRound)
        CGContextMoveToPoint(ctx, start_x, start_y)
        CGContextAddLineToPoint(ctx, end_x, end_y)
        CGContextStrokePath(ctx)

        # Draw main arrow shaft
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.2, 0.4, 0.7, 1.0))
        CGContextSetLineWidth(ctx, 6)
        CGContextMoveToPoint(ctx, start_x, start_y)
        CGContextAddLineToPoint(ctx, end_x, end_y)
        CGContextStrokePath(ctx)

        # Arrowhead
        angle = math.atan2(wv, wu)
        head_size = 18

        CGContextSetFillColorWithColor(ctx, self.create_color(0.2, 0.4, 0.7, 1.0))
        CGContextBeginPath(ctx)
        CGContextMoveToPoint(ctx, end_x, end_y)
        CGContextAddLineToPoint(ctx,
            end_x - head_size * math.cos(angle - 0.5),
            end_y - head_size * math.sin(angle - 0.5))
        CGContextAddLineToPoint(ctx,
            end_x - head_size * math.cos(angle + 0.5),
            end_y - head_size * math.sin(angle + 0.5))
        CGContextClosePath(ctx)
        CGContextFillPath(ctx)

        # Wind speed label - show direction wind is coming FROM
        direction = self._get_cardinal(wind_u, wind_v)
        label = f"Wind: {wind_speed:.1f} m/s from {direction}"
        self.draw_text_with_background(ctx, label, cx, cy - 50, font_size=13, bold=True,
                                       bg_color=(0.95, 0.97, 1.0, 0.95))

    def _get_cardinal(self, u: float, v: float) -> str:
        """Get cardinal direction wind is coming FROM."""
        # Wind blows TO (u,v), so it comes FROM (-u,-v)
        angle = math.degrees(math.atan2(-u, -v))
        if angle < 0:
            angle += 360

        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"]
        idx = int((angle + 22.5) / 45) % 8
        return directions[idx]

    def draw_wind_streamlines(self, ctx, x: float, y: float, wind_u: float, wind_v: float, wind_speed: float):
        """Draw wind streamlines passing through sensor, showing direction wind blows TO."""
        if wind_speed < 0.2:
            # Draw calm indicator with label
            CGContextSetStrokeColorWithColor(ctx, self.create_color(0.5, 0.6, 0.7, 0.6))
            CGContextSetLineWidth(ctx, 1.5)
            CGContextAddEllipseInRect(ctx, CGRectMake(x - 12, y - 12, 24, 24))
            CGContextStrokePath(ctx)
            self.draw_text_with_background(ctx, "Calm", x, y + 45, font_size=10, bold=True,
                                           bg_color=(0.9, 0.93, 0.97, 0.9))
            return

        wind_mag = math.sqrt(wind_u**2 + wind_v**2)
        if wind_mag < 0.01:
            return

        # Wind direction: u=east (right on screen), v=north
        # IMPORTANT: Screen coords have Y increasing downward, so negate v
        wu = wind_u / wind_mag
        wv = -wind_v / wind_mag  # Negate for screen coordinates (Y-flip)

        # Streamline parameters - extends both sides of sensor
        half_length = 80 + wind_speed * 25  # Half the total length (longer)
        num_lines = 3  # Multiple parallel streamlines
        line_spacing = 14

        # Perpendicular direction for spacing streamlines
        perp_u = -wv
        perp_v = wu

        CGContextSetLineCap(ctx, kCGLineCapRound)

        for line_idx in range(num_lines):
            # Offset perpendicular to wind direction
            offset = (line_idx - (num_lines - 1) / 2) * line_spacing
            center_x = x + perp_u * offset
            center_y = y + perp_v * offset

            # Start point (upwind side - where wind comes FROM)
            start_x = center_x - wu * half_length
            start_y = center_y - wv * half_length

            # End point (downwind side - where wind goes TO)
            end_x = center_x + wu * half_length
            end_y = center_y + wv * half_length

            # Draw streamline with gradient (fades at both ends, solid in middle)
            num_segments = 12
            for seg in range(num_segments):
                t1 = seg / num_segments
                t2 = (seg + 1) / num_segments

                # Position along full length (-0.5 to 0.5 centered on sensor)
                frac1 = t1 - 0.5
                frac2 = t2 - 0.5

                x1 = center_x + wu * half_length * 2 * frac1
                y1 = center_y + wv * half_length * 2 * frac1
                x2 = center_x + wu * half_length * 2 * frac2
                y2 = center_y + wv * half_length * 2 * frac2

                # Check bounds
                if not (self.map_x - 30 < x2 < self.map_x + self.map_width + 30 and
                        self.map_y - 30 < y2 < self.map_y + self.map_height + 30):
                    continue

                # Fade at ends, solid in middle
                dist_from_center = abs(t1 - 0.5) * 2  # 0 at center, 1 at ends
                alpha = 0.7 * (1 - dist_from_center * 0.7)
                width = 4.0 * (1 - dist_from_center * 0.3)  # Thicker lines

                CGContextSetStrokeColorWithColor(ctx, self.create_color(0.3, 0.5, 0.7, alpha))
                CGContextSetLineWidth(ctx, width)
                CGContextMoveToPoint(ctx, x1, y1)
                CGContextAddLineToPoint(ctx, x2, y2)
                CGContextStrokePath(ctx)

            # Draw arrowhead at the downwind end of the middle streamline
            if line_idx == num_lines // 2:
                arrow_x = center_x + wu * half_length * 0.9
                arrow_y = center_y + wv * half_length * 0.9

                angle = math.atan2(wv, wu)
                head_size = 14  # Bigger arrowhead

                CGContextSetFillColorWithColor(ctx, self.create_color(0.3, 0.5, 0.7, 0.7))
                CGContextBeginPath(ctx)
                CGContextMoveToPoint(ctx, arrow_x + head_size * math.cos(angle),
                                    arrow_y + head_size * math.sin(angle))
                CGContextAddLineToPoint(ctx,
                    arrow_x + head_size * 0.5 * math.cos(angle + 2.5),
                    arrow_y + head_size * 0.5 * math.sin(angle + 2.5))
                CGContextAddLineToPoint(ctx,
                    arrow_x + head_size * 0.5 * math.cos(angle - 2.5),
                    arrow_y + head_size * 0.5 * math.sin(angle - 2.5))
                CGContextClosePath(ctx)
                CGContextFillPath(ctx)

        # Wind label is now combined with sensor label, so don't draw here

    def draw_average_wind_arrow(self, ctx, wind_u: float, wind_v: float, wind_speed: float):
        """Draw average wind arrow in center of map."""
        cx = self.map_x + self.map_width / 2
        cy = self.map_y + self.map_height / 2

        if wind_speed < 0.2:
            # Calm indicator
            CGContextSetFillColorWithColor(ctx, self.create_color(0.85, 0.88, 0.92, 0.9))
            CGContextAddEllipseInRect(ctx, CGRectMake(cx - 35, cy - 35, 70, 70))
            CGContextFillPath(ctx)
            CGContextSetStrokeColorWithColor(ctx, self.create_color(0.5, 0.6, 0.7, 0.8))
            CGContextSetLineWidth(ctx, 2)
            CGContextAddEllipseInRect(ctx, CGRectMake(cx - 35, cy - 35, 70, 70))
            CGContextStrokePath(ctx)
            self.draw_text(ctx, "AVG", cx, cy + 8, font_size=11, bold=True, color=(0.4, 0.5, 0.6))
            self.draw_text(ctx, "CALM", cx, cy - 8, font_size=13, bold=True, color=(0.3, 0.4, 0.5))
            return

        wind_mag = math.sqrt(wind_u**2 + wind_v**2)
        if wind_mag < 0.01:
            return

        # IMPORTANT: Screen coords have Y increasing downward, so negate v
        wu = wind_u / wind_mag
        wv = -wind_v / wind_mag  # Negate for screen coordinates (Y-flip)

        # Arrow length based on wind speed
        arrow_len = 50 + wind_speed * 15

        # Draw background circle
        CGContextSetFillColorWithColor(ctx, self.create_color(0.92, 0.94, 0.97, 0.85))
        CGContextAddEllipseInRect(ctx, CGRectMake(cx - 45, cy - 45, 90, 90))
        CGContextFillPath(ctx)
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.6, 0.7, 0.8, 0.7))
        CGContextSetLineWidth(ctx, 1.5)
        CGContextAddEllipseInRect(ctx, CGRectMake(cx - 45, cy - 45, 90, 90))
        CGContextStrokePath(ctx)

        # Arrow shaft
        start_x = cx - wu * arrow_len / 2
        start_y = cy - wv * arrow_len / 2
        end_x = cx + wu * arrow_len / 2
        end_y = cy + wv * arrow_len / 2

        # White outline
        CGContextSetStrokeColorWithColor(ctx, self.create_color(1, 1, 1, 0.9))
        CGContextSetLineWidth(ctx, 8)
        CGContextSetLineCap(ctx, kCGLineCapRound)
        CGContextMoveToPoint(ctx, start_x, start_y)
        CGContextAddLineToPoint(ctx, end_x, end_y)
        CGContextStrokePath(ctx)

        # Main arrow
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.2, 0.4, 0.65, 1.0))
        CGContextSetLineWidth(ctx, 5)
        CGContextMoveToPoint(ctx, start_x, start_y)
        CGContextAddLineToPoint(ctx, end_x, end_y)
        CGContextStrokePath(ctx)

        # Arrowhead
        angle = math.atan2(wv, wu)
        head_size = 16

        CGContextSetFillColorWithColor(ctx, self.create_color(0.2, 0.4, 0.65, 1.0))
        CGContextBeginPath(ctx)
        CGContextMoveToPoint(ctx, end_x + head_size * 0.7 * math.cos(angle),
                            end_y + head_size * 0.7 * math.sin(angle))
        CGContextAddLineToPoint(ctx,
            end_x + head_size * 0.5 * math.cos(angle + 2.5),
            end_y + head_size * 0.5 * math.sin(angle + 2.5))
        CGContextAddLineToPoint(ctx,
            end_x + head_size * 0.5 * math.cos(angle - 2.5),
            end_y + head_size * 0.5 * math.sin(angle - 2.5))
        CGContextClosePath(ctx)
        CGContextFillPath(ctx)

        # Label
        direction = self._get_cardinal(wind_u, wind_v)
        label = f"Avg: {wind_speed:.1f} m/s from {direction}"
        self.draw_text_with_background(ctx, label, cx, cy - 55, font_size=11, bold=True,
                                       bg_color=(0.95, 0.96, 0.98, 0.95))

    def draw_smoke_plume(self, ctx, x: float, y: float, pollution: float,
                         wind_u: float, wind_v: float, wind_speed: float):
        """Draw smoke-like plume extending downwind from sensor."""
        if wind_speed < 0.3:
            return

        wind_mag = math.sqrt(wind_u**2 + wind_v**2)
        if wind_mag < 0.01:
            return

        # Wind components: u=east (right on screen), v=north
        # IMPORTANT: Screen coords have Y increasing downward, so negate v
        wu = wind_u / wind_mag
        wv = -wind_v / wind_mag  # Negate for screen coordinates (Y-flip)

        # Plume parameters
        normalized = self.get_log_normalized(pollution)
        base_length = 40 + wind_speed * 20
        base_width = 15 + normalized * 20

        color = self.get_aqi_color(pollution)

        # Draw gradient plume using circles
        num_segments = 15
        for i in range(num_segments):
            t = (i + 1) / num_segments

            # Position along wind direction
            px = x + wu * base_length * t
            py = y + wv * base_length * t

            # Check bounds
            if not (self.map_x < px < self.map_x + self.map_width and
                    self.map_y < py < self.map_y + self.map_height):
                continue

            # Width expands, opacity decreases
            width = base_width * (0.8 + t * 0.6)
            alpha = 0.25 * (1 - t * 0.8) * normalized

            CGContextSetFillColorWithColor(ctx, self.create_color(*color, alpha))
            CGContextAddEllipseInRect(ctx, CGRectMake(px - width/2, py - width/2, width, width))
            CGContextFillPath(ctx)

    def draw_sensor(self, ctx, lon: float, lat: float, pollution: float,
                    label: str, trend: float, wind_u: float = 0, wind_v: float = 0, wind_speed: float = 0):
        """Draw a sensor with clear pollution visualization and combined label."""
        x, y = self.geo_to_pixel(lon, lat)

        color = self.get_aqi_color(pollution)
        size = self.get_circle_size(pollution)

        # Outer glow
        for glow_mult, glow_alpha in [(1.6, 0.1), (1.3, 0.2)]:
            glow_size = size * glow_mult
            CGContextSetFillColorWithColor(ctx, self.create_color(*color, glow_alpha))
            CGContextAddEllipseInRect(ctx, CGRectMake(x - glow_size/2, y - glow_size/2, glow_size, glow_size))
            CGContextFillPath(ctx)

        # Main circle
        CGContextSetFillColorWithColor(ctx, self.create_color(*color, 0.9))
        CGContextAddEllipseInRect(ctx, CGRectMake(x - size/2, y - size/2, size, size))
        CGContextFillPath(ctx)

        # Border
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.2, 0.2, 0.2, 0.6))
        CGContextSetLineWidth(ctx, 2)
        CGContextAddEllipseInRect(ctx, CGRectMake(x - size/2, y - size/2, size, size))
        CGContextStrokePath(ctx)

        # Value inside circle (white text with shadow)
        value_text = self._format_value(pollution)

        # Determine text color based on background brightness
        brightness = color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114
        text_color = (0.1, 0.1, 0.1) if brightness > 0.5 else (1, 1, 1)

        # Shadow
        self.draw_text(ctx, value_text, x + 1, y - 1, font_size=14, bold=True,
                      color=(0, 0, 0, 0.3))
        # Main text
        self.draw_text(ctx, value_text, x, y, font_size=14, bold=True, color=text_color)

        # Trend arrow inside circle
        if abs(trend) > 500:
            arrow_y_offset = size * 0.25
            arrow_color = (0.1, 0.5, 0.1) if trend > 0 else (0.6, 0.1, 0.1)
            if brightness < 0.5:
                arrow_color = (0.5, 1.0, 0.5) if trend > 0 else (1.0, 0.5, 0.5)

            CGContextSetStrokeColorWithColor(ctx, self.create_color(*arrow_color, 0.9))
            CGContextSetLineWidth(ctx, 2.5)
            CGContextSetLineCap(ctx, kCGLineCapRound)

            if trend > 0:  # Up arrow
                CGContextMoveToPoint(ctx, x - 6, y + arrow_y_offset + 4)
                CGContextAddLineToPoint(ctx, x, y + arrow_y_offset - 4)
                CGContextAddLineToPoint(ctx, x + 6, y + arrow_y_offset + 4)
            else:  # Down arrow
                CGContextMoveToPoint(ctx, x - 6, y + arrow_y_offset - 4)
                CGContextAddLineToPoint(ctx, x, y + arrow_y_offset + 4)
                CGContextAddLineToPoint(ctx, x + 6, y + arrow_y_offset - 4)
            CGContextStrokePath(ctx)

        # Combined label above circle: pollution with units + wind
        pollution_label = f"{self._format_value(pollution)} p/cm³"
        if wind_speed >= 0.2:
            wind_dir = self._get_cardinal(wind_u, wind_v)
            wind_label = f"{wind_speed:.1f} m/s from {wind_dir}"
        else:
            wind_label = "Calm"

        # Draw pollution label (top)
        self.draw_text_with_background(ctx, pollution_label, x, y + size/2 + 22,
                                       font_size=12, bold=True,
                                       bg_color=(1, 1, 1, 0.92))
        # Draw wind label (below pollution)
        self.draw_text_with_background(ctx, wind_label, x, y + size/2 + 42,
                                       font_size=10, bold=False,
                                       bg_color=(0.92, 0.95, 0.98, 0.9))

    def _format_value(self, value: float) -> str:
        """Format pollution value for display."""
        if value >= 100000:
            return f"{value/1000:.0f}K"
        elif value >= 10000:
            return f"{value/1000:.1f}K"
        elif value >= 1000:
            return f"{value/1000:.1f}K"
        else:
            return f"{value:.0f}"

    def draw_dashboard(self, ctx, sensors: list):
        """Draw sensor dashboard on right side."""
        dash_x = self.width - self.RIGHT_MARGIN + 20
        dash_y = self.map_y + self.map_height - 50

        # Title
        self.draw_text(ctx, "Sensor Readings", dash_x + 70, dash_y,
                      font_size=14, bold=True, color=(0.2, 0.2, 0.2), center=True)

        bar_width = 120
        bar_height = 18

        for i, sensor in enumerate(sensors):
            # Handle both old (6-element) and new (9-element) tuple formats
            if len(sensor) >= 9:
                lon, lat, pollution, label, trend, upwindness, wind_u, wind_v, wind_speed = sensor
            else:
                lon, lat, pollution, label, trend, upwindness = sensor
                wind_u, wind_v, wind_speed = 0, 0, 0
            y = dash_y - 50 - i * 70

            # Sensor name
            self.draw_text(ctx, label, dash_x, y + 25, font_size=11, bold=True,
                          color=(0.3, 0.3, 0.3), center=False)

            # Value
            value_text = self._format_value(pollution)
            color = self.get_aqi_color(pollution)
            self.draw_text(ctx, value_text, dash_x + bar_width, y + 25,
                          font_size=16, bold=True, color=color, center=False)

            # Bar background
            CGContextSetFillColorWithColor(ctx, self.create_color(0.9, 0.9, 0.9))
            CGContextFillRect(ctx, CGRectMake(dash_x, y, bar_width, bar_height))

            # Bar fill (log scale)
            fill_width = self.get_log_normalized(pollution) * bar_width
            CGContextSetFillColorWithColor(ctx, self.create_color(*color, 0.85))
            CGContextFillRect(ctx, CGRectMake(dash_x, y, fill_width, bar_height))

            # Bar border
            CGContextSetStrokeColorWithColor(ctx, self.create_color(0.5, 0.5, 0.5))
            CGContextSetLineWidth(ctx, 1)
            CGContextAddRect(ctx, CGRectMake(dash_x, y, bar_width, bar_height))
            CGContextStrokePath(ctx)

            # Trend indicator
            if abs(trend) > 500:
                trend_text = "↑" if trend > 0 else "↓"
                trend_color = (0.2, 0.6, 0.2) if trend > 0 else (0.7, 0.2, 0.2)
                self.draw_text(ctx, trend_text, dash_x + bar_width + 55, y + 25,
                              font_size=18, bold=True, color=trend_color, center=False)

    def draw_legend(self, ctx):
        """Draw color scale legend."""
        legend_x = self.width - self.RIGHT_MARGIN + 20
        legend_y = self.map_y + 30
        bar_width = 20
        bar_height = 150

        # Title
        self.draw_text(ctx, "UFP Level", legend_x + 50, legend_y + bar_height + 25,
                      font_size=11, bold=True, color=(0.3, 0.3, 0.3), center=True)
        self.draw_text(ctx, "(particles/cm³)", legend_x + 50, legend_y + bar_height + 10,
                      font_size=9, bold=False, color=(0.5, 0.5, 0.5), center=True)

        # Color bar
        for i in range(int(bar_height)):
            t = i / bar_height
            # Map to log scale value
            log_val = self.log_min + t * (self.log_max - self.log_min)
            val = 10 ** log_val
            color = self.get_aqi_color(val)
            CGContextSetFillColorWithColor(ctx, self.create_color(*color))
            CGContextFillRect(ctx, CGRectMake(legend_x, legend_y + i, bar_width, 1))

        # Border
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.4, 0.4, 0.4))
        CGContextSetLineWidth(ctx, 1)
        CGContextAddRect(ctx, CGRectMake(legend_x, legend_y, bar_width, bar_height))
        CGContextStrokePath(ctx)

        # Labels (log scale)
        label_values = [1000, 5000, 20000, 100000, 300000]
        for val in label_values:
            if val < self.pollution_min or val > self.pollution_max:
                continue
            t = self.get_log_normalized(val)
            y = legend_y + t * bar_height

            text = f"{val/1000:.0f}K" if val >= 1000 else str(val)
            self.draw_text(ctx, text, legend_x + bar_width + 30, y,
                          font_size=9, bold=False, color=(0.3, 0.3, 0.3), center=True)

            # Tick mark
            CGContextMoveToPoint(ctx, legend_x + bar_width, y)
            CGContextAddLineToPoint(ctx, legend_x + bar_width + 4, y)
            CGContextStrokePath(ctx)

    def draw_title(self, ctx, title_date: str, time_label: str):
        """Draw title at top."""
        title = f"Air Quality Monitor — {title_date}"
        self.draw_text(ctx, title, self.width / 2, self.height - 35,
                      font_size=24, bold=True, color=(0.15, 0.15, 0.15))

        self.draw_text(ctx, f"Time: {time_label}", self.width / 2, self.height - 65,
                      font_size=16, bold=False, color=(0.4, 0.4, 0.4))

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
        CGContextSetFillColorWithColor(ctx, self.create_color(0.96, 0.96, 0.97))
        CGContextFillRect(ctx, CGRectMake(0, 0, self.width, self.height))

        # Map border
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.7, 0.7, 0.7))
        CGContextSetLineWidth(ctx, 1)
        CGContextAddRect(ctx, CGRectMake(self.map_x, self.map_y, self.map_width, self.map_height))
        CGContextStrokePath(ctx)

        # Base map
        if self.base_map_image:
            CGContextDrawImage(ctx, CGRectMake(self.map_x, self.map_y, self.map_width, self.map_height),
                             self.base_map_image)

        # Wind streamlines (draw first, behind everything)
        for sensor in frame.sensors:
            lon, lat, pollution, label, trend, upwindness, wind_u, wind_v, wind_speed = sensor
            x, y = self.geo_to_pixel(lon, lat)
            self.draw_wind_streamlines(ctx, x, y, wind_u, wind_v, wind_speed)

        # Smoke plumes (behind sensors, using per-sensor wind)
        for sensor in frame.sensors:
            lon, lat, pollution, label, trend, upwindness, wind_u, wind_v, wind_speed = sensor
            x, y = self.geo_to_pixel(lon, lat)
            self.draw_smoke_plume(ctx, x, y, pollution, wind_u, wind_v, wind_speed)

        # Sensors
        for sensor in frame.sensors:
            lon, lat, pollution, label, trend, upwindness, wind_u, wind_v, wind_speed = sensor
            self.draw_sensor(ctx, lon, lat, pollution, label, trend, wind_u, wind_v, wind_speed)

        # Average wind arrow in center of map
        self.draw_average_wind_arrow(ctx, frame.wind_u, frame.wind_v, frame.wind_speed)

        # Title
        title_date = frame.timestamp.strftime("%B %d, %Y")
        self.draw_title(ctx, title_date, frame.time_label)

        # Dashboard
        self.draw_dashboard(ctx, frame.sensors)

        # Legend
        self.draw_legend(ctx)

        return CGBitmapContextCreateImage(ctx)

    def save_image(self, image, path: str):
        url = NSURL.fileURLWithPath_(path)
        dest = CGImageDestinationCreateWithURL(url, "public.png", 1, None)
        CGImageDestinationAddImage(dest, image, None)
        CGImageDestinationFinalize(dest)

    def render_all_frames(self, frames: list, output_dir: str, num_workers: int = 8, start_frame: int = 1):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        total = len(frames)
        print(f"\nRendering {total} frames...")

        start_time = time.time()

        # Pre-warm CoreText to avoid lazy import race conditions in threads
        _ = CoreText.CTLineCreateWithAttributedString
        _ = CoreText.CTLineGetBoundsWithOptions
        _ = CoreText.CTLineDraw
        _ = CoreText.CTFontCreateWithName
        _ = CoreText.kCTFontAttributeName
        _ = CoreText.kCTForegroundColorFromContextAttributeName

        completed = [0]

        def render_one(args):
            i, frame = args
            image = self.render_frame(frame)
            frame_num = start_frame + i
            output_file = output_path / f"frame_{frame_num:05d}.png"
            self.save_image(image, str(output_file))
            completed[0] += 1
            if completed[0] % 50 == 0 or completed[0] == total:
                print(f"  {completed[0]}/{total} frames", flush=True)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            list(executor.map(render_one, enumerate(frames)))

        elapsed = time.time() - start_time
        print(f"  Done in {elapsed:.1f}s ({total/elapsed:.0f} fps)")
        return start_frame + total
