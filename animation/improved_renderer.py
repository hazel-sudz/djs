"""
Improved GPU renderer with intuitive wind-pollution visualization.

Key improvements:
1. Wind streamlines drawn directly on map (not in corner)
2. Pollution plumes extending downwind from each sensor
3. Transport arrows between sensors when wind connects them
4. Visual wind field showing air flow direction
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
    CGContextDrawPath,
    CGContextSetLineCap,
    CGContextSetLineJoin,
    CGContextAddRect,
    CGContextDrawImage,
    CGContextSaveGState,
    CGContextRestoreGState,
    CGContextSetAllowsAntialiasing,
    CGContextSetShouldAntialias,
    CGContextSetInterpolationQuality,
    CGContextSetAlpha,
    CGContextBeginPath,
    CGContextAddCurveToPoint,
    CGContextAddQuadCurveToPoint,
    CGImageDestinationCreateWithURL,
    CGImageDestinationAddImage,
    CGImageDestinationFinalize,
    kCGPathFillStroke,
    kCGLineCapRound,
    kCGLineJoinRound,
    kCGInterpolationHigh,
    CGColorCreate,
    CGRectMake,
)
import CoreFoundation
from Foundation import NSURL
import CoreText
from PIL import Image
import numpy as np


class ImprovedRenderer:
    """Renderer with intuitive wind-pollution visualization."""

    HEADER_HEIGHT = 85
    FOOTER_HEIGHT = 35
    LEFT_MARGIN = 25
    RIGHT_MARGIN = 130

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
        self.base_map_data = None

        self.map_x = self.LEFT_MARGIN
        self.map_y = self.FOOTER_HEIGHT
        self.map_width = width - self.LEFT_MARGIN - self.RIGHT_MARGIN
        self.map_height = height - self.HEADER_HEIGHT - self.FOOTER_HEIGHT

        print(f"Improved Renderer initialized: {width}x{height}, map area: {self.map_width}x{self.map_height}")

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

    def get_plasma_color(self, value: float) -> tuple:
        normalized = max(0, min(1, (value - self.pollution_min) / (self.pollution_max - self.pollution_min)))
        index = normalized * (len(self.PLASMA_COLORS) - 1)
        lower_idx = int(index)
        upper_idx = min(lower_idx + 1, len(self.PLASMA_COLORS) - 1)
        fraction = index - lower_idx
        lower, upper = self.PLASMA_COLORS[lower_idx], self.PLASMA_COLORS[upper_idx]
        return (lower[0] + (upper[0] - lower[0]) * fraction,
                lower[1] + (upper[1] - lower[1]) * fraction,
                lower[2] + (upper[2] - lower[2]) * fraction)

    def get_circle_size(self, pollution: float) -> float:
        normalized = (pollution - self.pollution_min) / (self.pollution_max - self.pollution_min)
        return 25 + normalized * 50

    def create_color(self, r: float, g: float, b: float, a: float = 1.0):
        return CGColorCreate(self.color_space, [r, g, b, a])

    def draw_wind_streamlines(self, ctx, wind_u: float, wind_v: float, wind_speed: float):
        """Draw wind flow lines across the map."""
        if wind_speed < 0.1:
            return

        wind_mag = math.sqrt(wind_u**2 + wind_v**2)
        if wind_mag < 0.01:
            return

        # Normalize wind direction
        wu = wind_u / wind_mag
        wv = wind_v / wind_mag

        # Wind angle (direction wind is blowing TO)
        wind_angle = math.atan2(wu, wv)

        # Draw multiple streamlines across the map
        num_lines = 7
        line_spacing = self.map_height / (num_lines + 1)

        # Calculate perpendicular direction for spacing
        perp_x = -wv
        perp_y = wu

        # Center of map
        cx = self.map_x + self.map_width / 2
        cy = self.map_y + self.map_height / 2

        # Arrow parameters
        arrow_length = min(self.map_width, self.map_height) * 0.15
        arrow_spacing = arrow_length * 1.8

        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.3, 0.5, 0.7, 0.5))
        CGContextSetLineWidth(ctx, 2.5)
        CGContextSetLineCap(ctx, kCGLineCapRound)

        for i in range(num_lines):
            # Offset from center perpendicular to wind
            offset = (i - num_lines // 2) * line_spacing
            start_offset_x = perp_x * offset
            start_offset_y = perp_y * offset

            # Starting point (upwind edge of map)
            # Go backwards from center along wind direction
            start_x = cx + start_offset_x - wu * self.map_width * 0.6
            start_y = cy + start_offset_y - wv * self.map_height * 0.6

            # Draw series of arrows along this streamline
            num_arrows = 4
            for j in range(num_arrows):
                ax = start_x + wu * arrow_spacing * j
                ay = start_y + wv * arrow_spacing * j

                # Check if arrow is within map bounds
                if (self.map_x < ax < self.map_x + self.map_width and
                    self.map_y < ay < self.map_y + self.map_height):

                    # Draw arrow line
                    end_x = ax + wu * arrow_length * 0.7
                    end_y = ay + wv * arrow_length * 0.7

                    CGContextMoveToPoint(ctx, ax, ay)
                    CGContextAddLineToPoint(ctx, end_x, end_y)
                    CGContextStrokePath(ctx)

                    # Draw arrowhead
                    head_size = 8
                    for da in [-0.5, 0.5]:
                        hx = end_x - head_size * math.cos(wind_angle + da)
                        hy = end_y - head_size * math.sin(wind_angle + da)
                        CGContextMoveToPoint(ctx, end_x, end_y)
                        CGContextAddLineToPoint(ctx, hx, hy)
                        CGContextStrokePath(ctx)

    def draw_pollution_plume(self, ctx, x: float, y: float, pollution: float,
                             wind_u: float, wind_v: float, wind_speed: float, color: tuple):
        """Draw a pollution plume extending downwind from a sensor."""
        if wind_speed < 0.2:
            return

        wind_mag = math.sqrt(wind_u**2 + wind_v**2)
        if wind_mag < 0.01:
            return

        # Normalize
        wu = wind_u / wind_mag
        wv = wind_v / wind_mag

        # Plume length based on pollution level and wind speed
        pollution_norm = (pollution - self.pollution_min) / (self.pollution_max - self.pollution_min)
        plume_length = 40 + pollution_norm * 80 + wind_speed * 15

        # Plume width
        plume_width = 15 + pollution_norm * 25

        # Draw gradient plume using multiple segments
        num_segments = 12
        for i in range(num_segments):
            t = i / num_segments
            alpha = 0.4 * (1 - t)  # Fade out along plume

            seg_x = x + wu * plume_length * t
            seg_y = y + wv * plume_length * t

            # Width expands along plume
            seg_width = plume_width * (0.5 + t * 0.8)

            CGContextSetFillColorWithColor(ctx, self.create_color(*color, alpha))
            CGContextAddEllipseInRect(ctx, CGRectMake(
                seg_x - seg_width/2, seg_y - seg_width/2, seg_width, seg_width
            ))
            CGContextFillPath(ctx)

    def draw_transport_arrows(self, ctx, sensors: list, wind_u: float, wind_v: float, wind_speed: float):
        """Draw arrows between sensors showing pollution transport direction."""
        if wind_speed < 0.3 or len(sensors) < 2:
            return

        wind_mag = math.sqrt(wind_u**2 + wind_v**2)
        if wind_mag < 0.01:
            return

        wu = wind_u / wind_mag
        wv = wind_v / wind_mag

        # For each pair of sensors, check if wind connects them
        sensor_positions = [(self.geo_to_pixel(s[0], s[1]), s[2]) for s in sensors]  # (pos, pollution)

        for i, (pos1, poll1) in enumerate(sensor_positions):
            for j, (pos2, poll2) in enumerate(sensor_positions):
                if i >= j:
                    continue

                # Vector from sensor i to sensor j
                dx = pos2[0] - pos1[0]
                dy = pos2[1] - pos1[1]
                dist = math.sqrt(dx**2 + dy**2)
                if dist < 10:
                    continue

                # Normalize
                dx /= dist
                dy /= dist

                # Check alignment with wind
                alignment = wu * dx + wv * dy

                if abs(alignment) > 0.5:  # Wind roughly connects these sensors
                    # Determine direction (wind goes from upwind to downwind)
                    if alignment > 0:
                        # Wind goes from 1 to 2
                        start, end = pos1, pos2
                        start_poll, end_poll = poll1, poll2
                    else:
                        # Wind goes from 2 to 1
                        start, end = pos2, pos1
                        start_poll, end_poll = poll2, poll1

                    # Color based on whether pollution increases or decreases along wind
                    if end_poll > start_poll * 1.1:
                        # Pollution increases downwind - accumulating
                        arrow_color = self.create_color(0.8, 0.3, 0.2, 0.6)
                    elif start_poll > end_poll * 1.1:
                        # Pollution decreases downwind - source at upwind
                        arrow_color = self.create_color(0.3, 0.6, 0.3, 0.6)
                    else:
                        # Similar levels
                        arrow_color = self.create_color(0.4, 0.4, 0.6, 0.4)

                    # Draw curved transport arrow
                    mid_x = (start[0] + end[0]) / 2
                    mid_y = (start[1] + end[1]) / 2

                    # Offset midpoint perpendicular to line
                    perp_x = -(end[1] - start[1]) / dist
                    perp_y = (end[0] - start[0]) / dist
                    curve_offset = dist * 0.15

                    ctrl_x = mid_x + perp_x * curve_offset
                    ctrl_y = mid_y + perp_y * curve_offset

                    CGContextSetStrokeColorWithColor(ctx, arrow_color)
                    CGContextSetLineWidth(ctx, 3)
                    CGContextSetLineCap(ctx, kCGLineCapRound)

                    # Draw curved line
                    CGContextMoveToPoint(ctx, start[0], start[1])
                    CGContextAddQuadCurveToPoint(ctx, ctrl_x, ctrl_y, end[0], end[1])
                    CGContextStrokePath(ctx)

                    # Arrowhead at end
                    angle = math.atan2(end[1] - ctrl_y, end[0] - ctrl_x)
                    head_size = 10
                    CGContextSetFillColorWithColor(ctx, arrow_color)
                    CGContextMoveToPoint(ctx, end[0], end[1])
                    CGContextAddLineToPoint(ctx,
                        end[0] - head_size * math.cos(angle - 0.4),
                        end[1] - head_size * math.sin(angle - 0.4))
                    CGContextAddLineToPoint(ctx,
                        end[0] - head_size * math.cos(angle + 0.4),
                        end[1] - head_size * math.sin(angle + 0.4))
                    CGContextFillPath(ctx)

    def draw_wind_source_indicator(self, ctx, wind_u: float, wind_v: float, wind_speed: float):
        """Draw a large 'wind coming from' indicator at map edge."""
        if wind_speed < 0.1:
            # Draw calm indicator
            cx = self.map_x + self.map_width / 2
            cy = self.map_y + self.map_height - 40
            self.draw_label(ctx, "Calm", cx, cy, font_size=14, bold=True,
                           bg_color=self.create_color(0.9, 0.9, 0.95, 0.9))
            return

        wind_mag = math.sqrt(wind_u**2 + wind_v**2)
        if wind_mag < 0.01:
            return

        # Wind is blowing TO direction (u, v), so it comes FROM (-u, -v)
        from_u = -wind_u / wind_mag
        from_v = -wind_v / wind_mag

        # Find edge position where wind enters
        # Calculate intersection with map boundary
        cx = self.map_x + self.map_width / 2
        cy = self.map_y + self.map_height / 2

        # Scale to reach edge
        scale_x = (self.map_width / 2 - 30) / abs(from_u) if abs(from_u) > 0.01 else 1e6
        scale_y = (self.map_height / 2 - 30) / abs(from_v) if abs(from_v) > 0.01 else 1e6
        scale = min(scale_x, scale_y)

        edge_x = cx + from_u * scale
        edge_y = cy + from_v * scale

        # Draw "WIND" label with direction
        direction_name = self._get_cardinal_direction(-from_u, -from_v)
        label = f"Wind: {wind_speed:.1f} m/s from {direction_name}"

        # Position label near where wind enters
        label_x = cx + from_u * scale * 0.7
        label_y = cy + from_v * scale * 0.7

        # Keep label within bounds
        label_x = max(self.map_x + 60, min(self.map_x + self.map_width - 60, label_x))
        label_y = max(self.map_y + 20, min(self.map_y + self.map_height - 20, label_y))

        self.draw_label(ctx, label, label_x, label_y, font_size=12, bold=True,
                       bg_color=self.create_color(0.85, 0.9, 0.95, 0.9))

        # Draw large arrow from edge pointing inward
        arrow_length = 50
        arrow_end_x = edge_x - from_u * arrow_length
        arrow_end_y = edge_y - from_v * arrow_length

        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.2, 0.4, 0.7, 0.8))
        CGContextSetFillColorWithColor(ctx, self.create_color(0.2, 0.4, 0.7, 0.8))
        CGContextSetLineWidth(ctx, 4)
        CGContextSetLineCap(ctx, kCGLineCapRound)

        CGContextMoveToPoint(ctx, edge_x, edge_y)
        CGContextAddLineToPoint(ctx, arrow_end_x, arrow_end_y)
        CGContextStrokePath(ctx)

        # Large arrowhead
        angle = math.atan2(-from_v, -from_u)
        head_size = 15
        CGContextMoveToPoint(ctx, arrow_end_x, arrow_end_y)
        CGContextAddLineToPoint(ctx,
            arrow_end_x - head_size * math.cos(angle - 0.4),
            arrow_end_y - head_size * math.sin(angle - 0.4))
        CGContextAddLineToPoint(ctx,
            arrow_end_x - head_size * math.cos(angle + 0.4),
            arrow_end_y - head_size * math.sin(angle + 0.4))
        CGContextFillPath(ctx)

    def _get_cardinal_direction(self, u: float, v: float) -> str:
        """Get cardinal direction name from wind components."""
        angle = math.degrees(math.atan2(u, v))
        if angle < 0:
            angle += 360

        directions = [
            (0, "N"), (45, "NE"), (90, "E"), (135, "SE"),
            (180, "S"), (225, "SW"), (270, "W"), (315, "NW"), (360, "N")
        ]

        for i in range(len(directions) - 1):
            if directions[i][0] <= angle < directions[i+1][0]:
                # Return closest
                if angle - directions[i][0] < directions[i+1][0] - angle:
                    return directions[i][1]
                else:
                    return directions[i+1][1]
        return "N"

    def draw_label(self, ctx, text: str, x: float, y: float, font_size: float = 12,
                   bold: bool = True, bg_color=None, padding: float = 6):
        font_name = "Helvetica-Bold" if bold else "Helvetica"
        font = CoreText.CTFontCreateWithName(font_name, font_size, None)
        attrs = {CoreText.kCTFontAttributeName: font, CoreText.kCTForegroundColorFromContextAttributeName: True}
        attr_string = CoreFoundation.CFAttributedStringCreate(None, text, attrs)
        line = CoreText.CTLineCreateWithAttributedString(attr_string)
        bounds = CoreText.CTLineGetBoundsWithOptions(line, 0)

        rect_w = bounds.size.width + padding * 2
        rect_h = bounds.size.height + padding * 2
        rect_x = x - rect_w / 2
        rect_y = y - rect_h / 2

        if bg_color:
            # Shadow
            CGContextSetFillColorWithColor(ctx, self.create_color(0, 0, 0, 0.1))
            CGContextFillRect(ctx, CGRectMake(rect_x + 2, rect_y - 2, rect_w, rect_h))
            # Background
            CGContextSetFillColorWithColor(ctx, bg_color)
            CGContextFillRect(ctx, CGRectMake(rect_x, rect_y, rect_w, rect_h))
            CGContextSetStrokeColorWithColor(ctx, self.create_color(0.6, 0.6, 0.6, 0.5))
            CGContextSetLineWidth(ctx, 0.5)
            CGContextAddRect(ctx, CGRectMake(rect_x, rect_y, rect_w, rect_h))
            CGContextStrokePath(ctx)

        CGContextSetFillColorWithColor(ctx, self.create_color(0.1, 0.1, 0.1))
        CGContextSaveGState(ctx)
        Quartz.CGContextSetTextPosition(ctx, rect_x + padding, rect_y + padding + 1)
        CoreText.CTLineDraw(line, ctx)
        CGContextRestoreGState(ctx)

    def draw_title(self, ctx, title_date: str, time_label: str):
        title_font = CoreText.CTFontCreateWithName("Helvetica-Bold", 22, None)
        title_attrs = {CoreText.kCTFontAttributeName: title_font, CoreText.kCTForegroundColorFromContextAttributeName: True}
        title = f"Ultrafine Particle Concentration — {title_date}"
        title_string = CoreFoundation.CFAttributedStringCreate(None, title, title_attrs)
        title_line = CoreText.CTLineCreateWithAttributedString(title_string)
        title_bounds = CoreText.CTLineGetBoundsWithOptions(title_line, 0)

        CGContextSetFillColorWithColor(ctx, self.create_color(0.15, 0.15, 0.15))
        CGContextSaveGState(ctx)
        Quartz.CGContextSetTextPosition(ctx, self.width/2 - title_bounds.size.width/2, self.height - 32)
        CoreText.CTLineDraw(title_line, ctx)
        CGContextRestoreGState(ctx)

        sub_font = CoreText.CTFontCreateWithName("Helvetica", 16, None)
        sub_attrs = {CoreText.kCTFontAttributeName: sub_font, CoreText.kCTForegroundColorFromContextAttributeName: True}
        sub_string = CoreFoundation.CFAttributedStringCreate(None, f"Time: {time_label}", sub_attrs)
        sub_line = CoreText.CTLineCreateWithAttributedString(sub_string)
        sub_bounds = CoreText.CTLineGetBoundsWithOptions(sub_line, 0)

        CGContextSetFillColorWithColor(ctx, self.create_color(0.4, 0.4, 0.4))
        CGContextSaveGState(ctx)
        Quartz.CGContextSetTextPosition(ctx, self.width/2 - sub_bounds.size.width/2, self.height - 58)
        CoreText.CTLineDraw(sub_line, ctx)
        CGContextRestoreGState(ctx)

    def draw_legend(self, ctx):
        legend_x = self.width - self.RIGHT_MARGIN + 15
        legend_y = self.map_y + 20
        bar_width = 16
        bar_height = 140

        # Title
        font = CoreText.CTFontCreateWithName("Helvetica-Bold", 9, None)
        attrs = {CoreText.kCTFontAttributeName: font, CoreText.kCTForegroundColorFromContextAttributeName: True}
        CGContextSetFillColorWithColor(ctx, self.create_color(0.2, 0.2, 0.2))

        for text, y_off in [("UFP (p/cm³)", 18)]:
            s = CoreFoundation.CFAttributedStringCreate(None, text, attrs)
            line = CoreText.CTLineCreateWithAttributedString(s)
            CGContextSaveGState(ctx)
            Quartz.CGContextSetTextPosition(ctx, legend_x, legend_y + bar_height + y_off)
            CoreText.CTLineDraw(line, ctx)
            CGContextRestoreGState(ctx)

        # Color bar
        for i in range(int(bar_height)):
            val = self.pollution_min + (self.pollution_max - self.pollution_min) * i / bar_height
            color = self.get_plasma_color(val)
            CGContextSetFillColorWithColor(ctx, self.create_color(*color))
            CGContextFillRect(ctx, CGRectMake(legend_x, legend_y + i, bar_width, 1))

        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.3, 0.3, 0.3))
        CGContextSetLineWidth(ctx, 1)
        CGContextAddRect(ctx, CGRectMake(legend_x, legend_y, bar_width, bar_height))
        CGContextStrokePath(ctx)

        # Labels
        label_font = CoreText.CTFontCreateWithName("Helvetica", 9, None)
        label_attrs = {CoreText.kCTFontAttributeName: label_font, CoreText.kCTForegroundColorFromContextAttributeName: True}
        CGContextSetFillColorWithColor(ctx, self.create_color(0.2, 0.2, 0.2))

        for val, y_pos in [(self.pollution_min, legend_y - 2), (self.pollution_max, legend_y + bar_height - 8)]:
            text = f"{val/1000:.0f}K" if val >= 1000 else f"{val:.0f}"
            s = CoreFoundation.CFAttributedStringCreate(None, text, label_attrs)
            line = CoreText.CTLineCreateWithAttributedString(s)
            CGContextSaveGState(ctx)
            Quartz.CGContextSetTextPosition(ctx, legend_x + bar_width + 4, y_pos)
            CoreText.CTLineDraw(line, ctx)
            CGContextRestoreGState(ctx)

        # Transport legend
        ty = legend_y + bar_height + 50
        self.draw_label(ctx, "Transport:", legend_x + 40, ty, font_size=9, bold=True)

        # Source indicator
        CGContextSetFillColorWithColor(ctx, self.create_color(0.3, 0.6, 0.3, 0.8))
        CGContextAddEllipseInRect(ctx, CGRectMake(legend_x, ty + 15, 10, 10))
        CGContextFillPath(ctx)
        self.draw_label(ctx, "Source", legend_x + 55, ty + 20, font_size=8, bold=False)

        # Accumulation indicator
        CGContextSetFillColorWithColor(ctx, self.create_color(0.8, 0.3, 0.2, 0.8))
        CGContextAddEllipseInRect(ctx, CGRectMake(legend_x, ty + 32, 10, 10))
        CGContextFillPath(ctx)
        self.draw_label(ctx, "Accumulating", legend_x + 55, ty + 37, font_size=8, bold=False)

    def render_frame(self, frame) -> bytes:
        ctx = CGBitmapContextCreate(
            None, self.width, self.height, 8, self.width * 4,
            self.color_space, Quartz.kCGImageAlphaPremultipliedLast
        )

        CGContextSetAllowsAntialiasing(ctx, True)
        CGContextSetShouldAntialias(ctx, True)
        CGContextSetInterpolationQuality(ctx, kCGInterpolationHigh)

        # Background
        CGContextSetFillColorWithColor(ctx, self.create_color(0.96, 0.96, 0.96))
        CGContextFillRect(ctx, CGRectMake(0, 0, self.width, self.height))

        # Map border
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.75, 0.75, 0.75))
        CGContextSetLineWidth(ctx, 1)
        CGContextAddRect(ctx, CGRectMake(self.map_x, self.map_y, self.map_width, self.map_height))
        CGContextStrokePath(ctx)

        # Base map
        if self.base_map_image:
            CGContextDrawImage(ctx, CGRectMake(self.map_x, self.map_y, self.map_width, self.map_height), self.base_map_image)

        # Wind streamlines (background)
        self.draw_wind_streamlines(ctx, frame.wind_u, frame.wind_v, frame.wind_speed)

        # Pollution plumes (before sensors so they appear behind)
        for sensor in frame.sensors:
            lon, lat, pollution, label, trend, upwindness = sensor
            pos = self.geo_to_pixel(lon, lat)
            color = self.get_plasma_color(pollution)
            self.draw_pollution_plume(ctx, pos[0], pos[1], pollution,
                                      frame.wind_u, frame.wind_v, frame.wind_speed, color)

        # Transport arrows between sensors
        self.draw_transport_arrows(ctx, frame.sensors, frame.wind_u, frame.wind_v, frame.wind_speed)

        # Draw sensors
        for sensor in frame.sensors:
            lon, lat, pollution, label, trend, upwindness = sensor
            pos = self.geo_to_pixel(lon, lat)
            size = self.get_circle_size(pollution)
            color = self.get_plasma_color(pollution)

            # Main circle with glow effect
            for glow in [1.4, 1.2, 1.0]:
                glow_alpha = 0.2 if glow > 1 else 0.85
                CGContextSetFillColorWithColor(ctx, self.create_color(*color, glow_alpha))
                glow_size = size * glow
                CGContextAddEllipseInRect(ctx, CGRectMake(pos[0] - glow_size/2, pos[1] - glow_size/2, glow_size, glow_size))
                CGContextFillPath(ctx)

            # Border
            CGContextSetStrokeColorWithColor(ctx, self.create_color(0.2, 0.2, 0.2, 0.5))
            CGContextSetLineWidth(ctx, 1.5)
            CGContextAddEllipseInRect(ctx, CGRectMake(pos[0] - size/2, pos[1] - size/2, size, size))
            CGContextStrokePath(ctx)

            # Trend indicator inside
            if abs(trend) > 500:
                if trend > 0:
                    CGContextSetStrokeColorWithColor(ctx, self.create_color(0.1, 0.4, 0.1, 0.9))
                else:
                    CGContextSetStrokeColorWithColor(ctx, self.create_color(0.5, 0.1, 0.1, 0.9))
                CGContextSetLineWidth(ctx, 2.5)
                arrow_len = min(12, size * 0.3)
                if trend > 0:
                    CGContextMoveToPoint(ctx, pos[0], pos[1] + arrow_len/2)
                    CGContextAddLineToPoint(ctx, pos[0], pos[1] - arrow_len/2)
                    CGContextMoveToPoint(ctx, pos[0] - 4, pos[1] - arrow_len/2 + 4)
                    CGContextAddLineToPoint(ctx, pos[0], pos[1] - arrow_len/2)
                    CGContextAddLineToPoint(ctx, pos[0] + 4, pos[1] - arrow_len/2 + 4)
                else:
                    CGContextMoveToPoint(ctx, pos[0], pos[1] - arrow_len/2)
                    CGContextAddLineToPoint(ctx, pos[0], pos[1] + arrow_len/2)
                    CGContextMoveToPoint(ctx, pos[0] - 4, pos[1] + arrow_len/2 - 4)
                    CGContextAddLineToPoint(ctx, pos[0], pos[1] + arrow_len/2)
                    CGContextAddLineToPoint(ctx, pos[0] + 4, pos[1] + arrow_len/2 - 4)
                CGContextStrokePath(ctx)

            # Label
            self.draw_label(ctx, label, pos[0], pos[1] + size/2 + 18, font_size=11, bold=True,
                           bg_color=self.create_color(1, 1, 1, 0.92))

        # Wind source indicator
        self.draw_wind_source_indicator(ctx, frame.wind_u, frame.wind_v, frame.wind_speed)

        # Title
        title_date = frame.timestamp.strftime("%B %d, %Y")
        self.draw_title(ctx, title_date, frame.time_label)

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
