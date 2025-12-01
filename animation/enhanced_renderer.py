"""
Enhanced GPU-accelerated frame renderer with pollution field visualization.

New features:
1. Interpolated pollution heatmap overlay
2. Wind arrow with transport indicator
3. Upwind/downwind sensor highlighting
4. Trend indicators on sensor labels
5. Wind-pollution correlation display
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
    CGContextAddRect,
    CGContextDrawImage,
    CGContextSaveGState,
    CGContextRestoreGState,
    CGContextSetAllowsAntialiasing,
    CGContextSetShouldAntialias,
    CGContextSetInterpolationQuality,
    CGContextSetAlpha,
    CGImageDestinationCreateWithURL,
    CGImageDestinationAddImage,
    CGImageDestinationFinalize,
    kCGPathFillStroke,
    kCGLineCapRound,
    kCGInterpolationHigh,
    CGColorCreate,
    CGRectMake,
)
import CoreFoundation
from Foundation import NSURL
import CoreText
from PIL import Image
import numpy as np


class EnhancedMetalRenderer:
    """Enhanced GPU-accelerated frame renderer with pollution field visualization."""

    HEADER_HEIGHT = 90
    FOOTER_HEIGHT = 40
    LEFT_MARGIN = 30
    RIGHT_MARGIN = 160

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
        self.base_map_data = None

        self.map_x = self.LEFT_MARGIN
        self.map_y = self.FOOTER_HEIGHT
        self.map_width = width - self.LEFT_MARGIN - self.RIGHT_MARGIN
        self.map_height = height - self.HEADER_HEIGHT - self.FOOTER_HEIGHT

        print(f"Enhanced Metal Renderer initialized")
        print(f"  Resolution: {width}x{height}")
        print(f"  Map area: {self.map_width}x{self.map_height}")

    def load_base_map(self, path: str):
        """Load pre-rendered base map image."""
        pil_image = Image.open(path).convert('RGBA')
        pil_image = pil_image.resize((self.map_width, self.map_height), Image.LANCZOS)

        img_array = np.array(pil_image)
        self.base_map_data = img_array.tobytes()
        provider = Quartz.CGDataProviderCreateWithData(
            None, self.base_map_data, len(self.base_map_data), None
        )

        self.base_map_image = Quartz.CGImageCreate(
            self.map_width, self.map_height, 8, 32, self.map_width * 4,
            self.color_space, Quartz.kCGImageAlphaPremultipliedLast,
            provider, None, True, Quartz.kCGRenderingIntentDefault
        )
        print(f"  Base map loaded: {path}")

    def geo_to_pixel(self, lon: float, lat: float) -> tuple:
        """Convert geographic coordinates to pixel coordinates."""
        rel_x = (lon - self.map_extent.lon_min) / (self.map_extent.lon_max - self.map_extent.lon_min)
        rel_y = 1.0 - (lat - self.map_extent.lat_min) / (self.map_extent.lat_max - self.map_extent.lat_min)
        x = self.map_x + rel_x * self.map_width
        y = self.map_y + rel_y * self.map_height
        return (x, y)

    def get_plasma_color(self, value: float) -> tuple:
        """Get color from plasma colormap."""
        normalized = max(0, min(1, (value - self.pollution_min) / (self.pollution_max - self.pollution_min)))
        index = normalized * (len(self.PLASMA_COLORS) - 1)
        lower_idx = int(index)
        upper_idx = min(lower_idx + 1, len(self.PLASMA_COLORS) - 1)
        fraction = index - lower_idx
        lower, upper = self.PLASMA_COLORS[lower_idx], self.PLASMA_COLORS[upper_idx]
        return (
            lower[0] + (upper[0] - lower[0]) * fraction,
            lower[1] + (upper[1] - lower[1]) * fraction,
            lower[2] + (upper[2] - lower[2]) * fraction,
        )

    def get_circle_size(self, pollution: float) -> float:
        normalized = (pollution - self.pollution_min) / (self.pollution_max - self.pollution_min)
        return 22 + normalized * 55

    def create_color(self, r: float, g: float, b: float, a: float = 1.0):
        return CGColorCreate(self.color_space, [r, g, b, a])

    def create_pollution_field_image(self, field: np.ndarray) -> tuple:
        """Convert pollution field to RGBA image data."""
        h, w = field.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)

        for i in range(h):
            for j in range(w):
                r, g, b = self.get_plasma_color(field[i, j])
                rgba[i, j] = [int(r * 255), int(g * 255), int(b * 255), 100]

        # Flip vertically for CG coordinate system
        rgba = np.flipud(rgba)
        return rgba.tobytes(), w, h

    def draw_rounded_rect(self, ctx, x: float, y: float, w: float, h: float,
                          radius: float, fill_color, stroke_color=None):
        CGContextSaveGState(ctx)
        CGContextMoveToPoint(ctx, x + radius, y)
        CGContextAddLineToPoint(ctx, x + w - radius, y)
        Quartz.CGContextAddArcToPoint(ctx, x + w, y, x + w, y + radius, radius)
        CGContextAddLineToPoint(ctx, x + w, y + h - radius)
        Quartz.CGContextAddArcToPoint(ctx, x + w, y + h, x + w - radius, y + h, radius)
        CGContextAddLineToPoint(ctx, x + radius, y + h)
        Quartz.CGContextAddArcToPoint(ctx, x, y + h, x, y + h - radius, radius)
        CGContextAddLineToPoint(ctx, x, y + radius)
        Quartz.CGContextAddArcToPoint(ctx, x, y, x + radius, y, radius)
        Quartz.CGContextClosePath(ctx)
        CGContextSetFillColorWithColor(ctx, fill_color)
        if stroke_color:
            CGContextSetStrokeColorWithColor(ctx, stroke_color)
            CGContextSetLineWidth(ctx, 0.5)
            CGContextDrawPath(ctx, kCGPathFillStroke)
        else:
            CGContextFillPath(ctx)
        CGContextRestoreGState(ctx)

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
            shadow_color = self.create_color(0, 0, 0, 0.12)
            self.draw_rounded_rect(ctx, rect_x + 2, rect_y - 2, rect_w, rect_h, 5, shadow_color)
            # Background
            self.draw_rounded_rect(ctx, rect_x, rect_y, rect_w, rect_h, 5, bg_color,
                                   self.create_color(0.5, 0.5, 0.5, 0.4))

        CGContextSetFillColorWithColor(ctx, self.create_color(0.1, 0.1, 0.1))
        CGContextSaveGState(ctx)
        Quartz.CGContextSetTextPosition(ctx, rect_x + padding, rect_y + padding + 1)
        CoreText.CTLineDraw(line, ctx)
        CGContextRestoreGState(ctx)

    def draw_wind_compass(self, ctx, wind_u: float, wind_v: float, wind_speed: float,
                           transport_indicator: str, alignment: float):
        """Draw wind compass with transport information in corner."""
        cx = self.width - self.RIGHT_MARGIN + 70
        cy = self.height - 60
        radius = 35

        # Background circle
        CGContextSetFillColorWithColor(ctx, self.create_color(0.97, 0.97, 0.97, 0.95))
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.7, 0.7, 0.7))
        CGContextSetLineWidth(ctx, 1)
        CGContextAddEllipseInRect(ctx, CGRectMake(cx - radius, cy - radius, radius * 2, radius * 2))
        CGContextDrawPath(ctx, kCGPathFillStroke)

        # Cardinal directions
        font = CoreText.CTFontCreateWithName("Helvetica", 9, None)
        attrs = {CoreText.kCTFontAttributeName: font, CoreText.kCTForegroundColorFromContextAttributeName: True}
        CGContextSetFillColorWithColor(ctx, self.create_color(0.4, 0.4, 0.4))
        for label, angle in [("N", 90), ("E", 0), ("S", -90), ("W", 180)]:
            lx = cx + (radius - 10) * math.cos(math.radians(angle))
            ly = cy + (radius - 10) * math.sin(math.radians(angle))
            s = CoreFoundation.CFAttributedStringCreate(None, label, attrs)
            line = CoreText.CTLineCreateWithAttributedString(s)
            CGContextSaveGState(ctx)
            Quartz.CGContextSetTextPosition(ctx, lx - 3, ly - 4)
            CoreText.CTLineDraw(line, ctx)
            CGContextRestoreGState(ctx)

        # Wind arrow (from center, pointing in wind direction)
        if wind_speed > 0.1:
            wind_mag = math.sqrt(wind_u**2 + wind_v**2)
            if wind_mag > 0:
                arrow_len = min(radius - 15, wind_speed * 4)
                end_x = cx + (wind_u / wind_mag) * arrow_len
                end_y = cy + (wind_v / wind_mag) * arrow_len

                # Color based on transport
                if transport_indicator == "accumulating":
                    color = self.create_color(0.8, 0.2, 0.2, 0.9)
                elif transport_indicator == "dispersing":
                    color = self.create_color(0.2, 0.6, 0.2, 0.9)
                else:
                    color = self.create_color(0.2, 0.2, 0.7, 0.9)

                CGContextSetStrokeColorWithColor(ctx, color)
                CGContextSetFillColorWithColor(ctx, color)
                CGContextSetLineWidth(ctx, 3)
                CGContextSetLineCap(ctx, kCGLineCapRound)
                CGContextMoveToPoint(ctx, cx, cy)
                CGContextAddLineToPoint(ctx, end_x, end_y)
                CGContextStrokePath(ctx)

                # Arrowhead
                angle = math.atan2(end_y - cy, end_x - cx)
                for da in [-0.4, 0.4]:
                    px = end_x - 8 * math.cos(angle + da)
                    py = end_y - 8 * math.sin(angle + da)
                    CGContextMoveToPoint(ctx, end_x, end_y)
                    CGContextAddLineToPoint(ctx, px, py)
                    CGContextStrokePath(ctx)

        # Wind speed label
        speed_text = f"{wind_speed:.1f} m/s"
        self.draw_label(ctx, speed_text, cx, cy - radius - 15, font_size=10, bold=True,
                       bg_color=self.create_color(0.95, 0.95, 0.95, 0.9))

        # Transport indicator
        indicator_colors = {
            "accumulating": (0.95, 0.85, 0.85),
            "dispersing": (0.85, 0.95, 0.85),
            "mixing": (0.85, 0.85, 0.95),
            "calm": (0.9, 0.9, 0.9)
        }
        ic = indicator_colors.get(transport_indicator, (0.9, 0.9, 0.9))
        self.draw_label(ctx, transport_indicator.capitalize(), cx, cy + radius + 15,
                       font_size=9, bold=True, bg_color=self.create_color(*ic, 0.9))

    def draw_title(self, ctx, title_date: str, time_label: str):
        # Title
        title_font = CoreText.CTFontCreateWithName("Helvetica-Bold", 22, None)
        title_attrs = {CoreText.kCTFontAttributeName: title_font, CoreText.kCTForegroundColorFromContextAttributeName: True}
        title = f"Ultrafine Particle Concentration — {title_date}"
        title_string = CoreFoundation.CFAttributedStringCreate(None, title, title_attrs)
        title_line = CoreText.CTLineCreateWithAttributedString(title_string)
        title_bounds = CoreText.CTLineGetBoundsWithOptions(title_line, 0)

        CGContextSetFillColorWithColor(ctx, self.create_color(0.15, 0.15, 0.15))
        CGContextSaveGState(ctx)
        Quartz.CGContextSetTextPosition(ctx, self.width/2 - title_bounds.size.width/2, self.height - 35)
        CoreText.CTLineDraw(title_line, ctx)
        CGContextRestoreGState(ctx)

        # Subtitle
        sub_font = CoreText.CTFontCreateWithName("Helvetica", 16, None)
        sub_attrs = {CoreText.kCTFontAttributeName: sub_font, CoreText.kCTForegroundColorFromContextAttributeName: True}
        sub_string = CoreFoundation.CFAttributedStringCreate(None, f"Time: {time_label}", sub_attrs)
        sub_line = CoreText.CTLineCreateWithAttributedString(sub_string)
        sub_bounds = CoreText.CTLineGetBoundsWithOptions(sub_line, 0)

        CGContextSetFillColorWithColor(ctx, self.create_color(0.4, 0.4, 0.4))
        CGContextSaveGState(ctx)
        Quartz.CGContextSetTextPosition(ctx, self.width/2 - sub_bounds.size.width/2, self.height - 60)
        CoreText.CTLineDraw(sub_line, ctx)
        CGContextRestoreGState(ctx)

    def draw_legend(self, ctx):
        """Draw the color legend."""
        legend_x = self.width - self.RIGHT_MARGIN + 25
        legend_y = self.map_y + 30
        bar_width = 18
        bar_height = 160

        # Title
        font = CoreText.CTFontCreateWithName("Helvetica-Bold", 10, None)
        attrs = {CoreText.kCTFontAttributeName: font, CoreText.kCTForegroundColorFromContextAttributeName: True}
        CGContextSetFillColorWithColor(ctx, self.create_color(0.2, 0.2, 0.2))

        for text, y_off in [("UFP Concentration", 32), ("(particles/cm³)", 18)]:
            s = CoreFoundation.CFAttributedStringCreate(None, text, attrs)
            line = CoreText.CTLineCreateWithAttributedString(s)
            CGContextSaveGState(ctx)
            Quartz.CGContextSetTextPosition(ctx, legend_x - 5, legend_y + bar_height + y_off)
            CoreText.CTLineDraw(line, ctx)
            CGContextRestoreGState(ctx)

        # Color bar
        for i in range(int(bar_height)):
            val = self.pollution_min + (self.pollution_max - self.pollution_min) * i / bar_height
            color = self.get_plasma_color(val)
            CGContextSetFillColorWithColor(ctx, self.create_color(*color))
            CGContextFillRect(ctx, CGRectMake(legend_x, legend_y + i, bar_width, 1))

        # Border
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
            Quartz.CGContextSetTextPosition(ctx, legend_x + bar_width + 5, y_pos)
            CoreText.CTLineDraw(line, ctx)
            CGContextRestoreGState(ctx)

    def render_frame(self, frame) -> bytes:
        """Render a single enhanced frame."""
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

        # Pollution field overlay
        if frame.pollution_field is not None:
            field_data, fw, fh = self.create_pollution_field_image(frame.pollution_field)
            provider = Quartz.CGDataProviderCreateWithData(None, field_data, len(field_data), None)
            field_image = Quartz.CGImageCreate(
                fw, fh, 8, 32, fw * 4, self.color_space,
                Quartz.kCGImageAlphaPremultipliedLast, provider, None, True,
                Quartz.kCGRenderingIntentDefault
            )
            CGContextSaveGState(ctx)
            CGContextSetAlpha(ctx, 0.4)
            CGContextDrawImage(ctx, CGRectMake(self.map_x, self.map_y, self.map_width, self.map_height),
                             field_image)
            CGContextRestoreGState(ctx)

        # Draw sensors
        for sensor in frame.sensors:
            lon, lat, pollution, label, trend, upwindness, *_wind = sensor
            pos = self.geo_to_pixel(lon, lat)
            size = self.get_circle_size(pollution)
            color = self.get_plasma_color(pollution)

            # Upwind/downwind indicator ring
            if abs(upwindness) > 0.3:
                ring_color = self.create_color(0.2, 0.5, 0.8, 0.6) if upwindness > 0 else self.create_color(0.8, 0.4, 0.2, 0.6)
                CGContextSetStrokeColorWithColor(ctx, ring_color)
                CGContextSetLineWidth(ctx, 3)
                CGContextAddEllipseInRect(ctx, CGRectMake(pos[0] - size/2 - 4, pos[1] - size/2 - 4, size + 8, size + 8))
                CGContextStrokePath(ctx)

            # Main circle
            CGContextSetFillColorWithColor(ctx, self.create_color(*color, 0.8))
            CGContextAddEllipseInRect(ctx, CGRectMake(pos[0] - size/2, pos[1] - size/2, size, size))
            CGContextFillPath(ctx)

            # Circle border
            CGContextSetStrokeColorWithColor(ctx, self.create_color(*color, 1.0))
            CGContextSetLineWidth(ctx, 2)
            CGContextAddEllipseInRect(ctx, CGRectMake(pos[0] - size/2, pos[1] - size/2, size, size))
            CGContextStrokePath(ctx)

            # Trend arrow inside circle
            if abs(trend) > 300:
                arrow_color = self.create_color(0.1, 0.5, 0.1) if trend > 0 else self.create_color(0.6, 0.1, 0.1)
                CGContextSetStrokeColorWithColor(ctx, arrow_color)
                CGContextSetLineWidth(ctx, 2.5)
                arrow_len = 12
                if trend > 0:
                    CGContextMoveToPoint(ctx, pos[0], pos[1] - arrow_len/2)
                    CGContextAddLineToPoint(ctx, pos[0], pos[1] + arrow_len/2)
                    CGContextMoveToPoint(ctx, pos[0] - 4, pos[1] + arrow_len/2 - 4)
                    CGContextAddLineToPoint(ctx, pos[0], pos[1] + arrow_len/2)
                    CGContextAddLineToPoint(ctx, pos[0] + 4, pos[1] + arrow_len/2 - 4)
                else:
                    CGContextMoveToPoint(ctx, pos[0], pos[1] + arrow_len/2)
                    CGContextAddLineToPoint(ctx, pos[0], pos[1] - arrow_len/2)
                    CGContextMoveToPoint(ctx, pos[0] - 4, pos[1] - arrow_len/2 + 4)
                    CGContextAddLineToPoint(ctx, pos[0], pos[1] - arrow_len/2)
                    CGContextAddLineToPoint(ctx, pos[0] + 4, pos[1] - arrow_len/2 + 4)
                CGContextStrokePath(ctx)

            # Label
            self.draw_label(ctx, label, pos[0], pos[1] + size/2 + 16, font_size=11, bold=True,
                           bg_color=self.create_color(1, 1, 1, 0.95))

        # Wind compass
        self.draw_wind_compass(ctx, frame.wind_u, frame.wind_v, frame.wind_speed,
                               frame.transport_indicator, frame.wind_pollution_alignment)

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

    def render_all_frames(self, frames: list, output_dir: str, num_workers: int = 8):
        """Render all frames in parallel."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        total = len(frames)
        print(f"\nRendering {total} frames with Metal GPU...")

        start_time = time.time()
        completed = [0]

        def render_one(args):
            i, frame = args
            image = self.render_frame(frame)
            output_file = output_path / f"frame_{i+1:04d}.png"
            self.save_image(image, str(output_file))
            completed[0] += 1
            progress = (completed[0] * 100) // total
            print(f"\rProgress: {progress}% ({completed[0]}/{total} frames)", end="", flush=True)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            list(executor.map(render_one, enumerate(frames)))

        elapsed = time.time() - start_time
        print(f"\n\nRendering complete!")
        print(f"  Total time: {elapsed:.1f} seconds")
        print(f"  Average: {elapsed/total:.3f} seconds per frame")
        print(f"  Throughput: {total/elapsed*60:.1f} frames per minute")
