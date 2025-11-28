"""
GPU-accelerated frame renderer using Core Graphics (Metal on M2).

This module uses PyObjC to access Apple's Core Graphics framework,
which is hardware-accelerated via Metal on Apple Silicon.
"""

import math
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time

# Core Graphics via PyObjC (Metal-accelerated on M2)
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
    CGImageDestinationCreateWithURL,
    CGImageDestinationAddImage,
    CGImageDestinationFinalize,
    kCGPathFillStroke,
    kCGLineCapRound,
    kCGInterpolationHigh,
    CGColorCreate,
    CGRectMake,
    CGPointMake,
)
import CoreFoundation
from Foundation import NSURL
import CoreText

# Image loading
from PIL import Image
import numpy as np


@dataclass
class FrameData:
    frame_number: int
    time_label: str
    title_date: str
    sensors: list  # List of (lon, lat, pollution, label)
    wind: Optional[dict]  # {center_lon, center_lat, end_lon, end_lat, speed_label}


class MetalRenderer:
    """GPU-accelerated frame renderer using Core Graphics (Metal on M2)."""

    # Layout constants for margins
    HEADER_HEIGHT = 80       # Space for title at top
    FOOTER_HEIGHT = 30       # Space at bottom
    LEFT_MARGIN = 30         # Left padding
    RIGHT_MARGIN = 140       # Right side for legend

    # Plasma colormap (matching viridis plasma from R)
    PLASMA_COLORS = [
        (0.050, 0.030, 0.528),
        (0.133, 0.022, 0.563),
        (0.208, 0.020, 0.588),
        (0.282, 0.024, 0.602),
        (0.352, 0.034, 0.607),
        (0.417, 0.050, 0.601),
        (0.478, 0.071, 0.586),
        (0.536, 0.095, 0.563),
        (0.591, 0.121, 0.533),
        (0.643, 0.150, 0.498),
        (0.692, 0.180, 0.459),
        (0.738, 0.213, 0.418),
        (0.781, 0.248, 0.375),
        (0.821, 0.286, 0.332),
        (0.857, 0.326, 0.289),
        (0.890, 0.369, 0.246),
        (0.918, 0.416, 0.204),
        (0.942, 0.466, 0.163),
        (0.960, 0.520, 0.124),
        (0.973, 0.578, 0.089),
        (0.981, 0.639, 0.058),
        (0.984, 0.702, 0.038),
        (0.981, 0.768, 0.034),
        (0.972, 0.834, 0.053),
        (0.959, 0.899, 0.101),
        (0.940, 0.975, 0.131),
    ]

    def __init__(
        self,
        width: int,
        height: int,
        map_extent: 'MapExtent',
        pollution_min: float,
        pollution_max: float,
    ):
        self.width = width
        self.height = height
        self.map_extent = map_extent
        self.pollution_min = pollution_min
        self.pollution_max = pollution_max
        self.color_space = CGColorSpaceCreateDeviceRGB()
        self.base_map_image = None
        self.base_map_data = None

        # Calculate map area dimensions (within margins)
        self.map_x = self.LEFT_MARGIN
        self.map_y = self.FOOTER_HEIGHT
        self.map_width = width - self.LEFT_MARGIN - self.RIGHT_MARGIN
        self.map_height = height - self.HEADER_HEIGHT - self.FOOTER_HEIGHT

        print(f"Metal GPU Renderer initialized")
        print(f"  Resolution: {width}x{height}")
        print(f"  Map area: {self.map_width}x{self.map_height}")

    def load_base_map(self, path: str):
        """Load pre-rendered base map image."""
        pil_image = Image.open(path).convert('RGBA')
        # Resize to fit map area
        pil_image = pil_image.resize((self.map_width, self.map_height), Image.LANCZOS)

        img_array = np.array(pil_image)
        self.base_map_data = img_array.tobytes()
        provider = Quartz.CGDataProviderCreateWithData(
            None, self.base_map_data, len(self.base_map_data), None
        )

        self.base_map_image = Quartz.CGImageCreate(
            self.map_width, self.map_height,
            8, 32, self.map_width * 4,
            self.color_space,
            Quartz.kCGImageAlphaPremultipliedLast,
            provider,
            None, True,
            Quartz.kCGRenderingIntentDefault
        )

        print(f"  Base map loaded: {path}")

    def geo_to_pixel(self, lon: float, lat: float) -> tuple[float, float]:
        """Convert geographic coordinates to pixel coordinates within map area."""
        # Calculate position within map area
        rel_x = (lon - self.map_extent.lon_min) / (self.map_extent.lon_max - self.map_extent.lon_min)
        rel_y = 1.0 - (lat - self.map_extent.lat_min) / (self.map_extent.lat_max - self.map_extent.lat_min)

        # Convert to absolute pixel position (accounting for margins)
        x = self.map_x + rel_x * self.map_width
        y = self.map_y + rel_y * self.map_height
        return (x, y)

    def get_plasma_color(self, value: float) -> tuple[float, float, float]:
        """Get color from plasma colormap."""
        normalized = max(0, min(1, (value - self.pollution_min) / (self.pollution_max - self.pollution_min)))
        index = normalized * (len(self.PLASMA_COLORS) - 1)
        lower_idx = int(index)
        upper_idx = min(lower_idx + 1, len(self.PLASMA_COLORS) - 1)
        fraction = index - lower_idx

        lower = self.PLASMA_COLORS[lower_idx]
        upper = self.PLASMA_COLORS[upper_idx]

        return (
            lower[0] + (upper[0] - lower[0]) * fraction,
            lower[1] + (upper[1] - lower[1]) * fraction,
            lower[2] + (upper[2] - lower[2]) * fraction,
        )

    def get_circle_size(self, pollution: float) -> float:
        """Calculate circle size based on pollution value."""
        normalized = (pollution - self.pollution_min) / (self.pollution_max - self.pollution_min)
        min_size = 20
        max_size = 70
        return min_size + normalized * (max_size - min_size)

    def create_color(self, r: float, g: float, b: float, a: float = 1.0):
        """Create a CGColor."""
        return CGColorCreate(self.color_space, [r, g, b, a])

    def draw_rounded_rect(self, ctx, x: float, y: float, width: float, height: float,
                          radius: float, fill_color, stroke_color=None, stroke_width: float = 1):
        """Draw a rounded rectangle."""
        # Simple rounded rect using arcs
        CGContextSaveGState(ctx)

        # Create path for rounded rect
        CGContextMoveToPoint(ctx, x + radius, y)
        CGContextAddLineToPoint(ctx, x + width - radius, y)
        Quartz.CGContextAddArcToPoint(ctx, x + width, y, x + width, y + radius, radius)
        CGContextAddLineToPoint(ctx, x + width, y + height - radius)
        Quartz.CGContextAddArcToPoint(ctx, x + width, y + height, x + width - radius, y + height, radius)
        CGContextAddLineToPoint(ctx, x + radius, y + height)
        Quartz.CGContextAddArcToPoint(ctx, x, y + height, x, y + height - radius, radius)
        CGContextAddLineToPoint(ctx, x, y + radius)
        Quartz.CGContextAddArcToPoint(ctx, x, y, x + radius, y, radius)
        Quartz.CGContextClosePath(ctx)

        CGContextSetFillColorWithColor(ctx, fill_color)
        if stroke_color:
            CGContextSetStrokeColorWithColor(ctx, stroke_color)
            CGContextSetLineWidth(ctx, stroke_width)
            CGContextDrawPath(ctx, kCGPathFillStroke)
        else:
            CGContextFillPath(ctx)

        CGContextRestoreGState(ctx)

    def draw_label(self, ctx, text: str, x: float, y: float, font_size: float = 13,
                   bold: bool = True, bg_color=None, text_color=None, padding: float = 8,
                   corner_radius: float = 6, shadow: bool = True):
        """Draw a styled label with background."""
        font_name = "Helvetica-Bold" if bold else "Helvetica"
        font = CoreText.CTFontCreateWithName(font_name, font_size, None)

        attrs = {
            CoreText.kCTFontAttributeName: font,
            CoreText.kCTForegroundColorFromContextAttributeName: True,
        }
        attr_string = CoreFoundation.CFAttributedStringCreate(None, text, attrs)
        line = CoreText.CTLineCreateWithAttributedString(attr_string)
        bounds = CoreText.CTLineGetBoundsWithOptions(line, 0)

        text_width = bounds.size.width
        text_height = bounds.size.height

        rect_width = text_width + padding * 2
        rect_height = text_height + padding * 2
        rect_x = x - rect_width / 2
        rect_y = y - rect_height / 2

        # Draw shadow
        if shadow and bg_color:
            shadow_offset = 2
            shadow_color = self.create_color(0, 0, 0, 0.15)
            self.draw_rounded_rect(ctx, rect_x + shadow_offset, rect_y - shadow_offset,
                                   rect_width, rect_height, corner_radius, shadow_color)

        # Draw background
        if bg_color:
            border_color = self.create_color(0.6, 0.6, 0.6, 0.5)
            self.draw_rounded_rect(ctx, rect_x, rect_y, rect_width, rect_height,
                                   corner_radius, bg_color, border_color, 0.5)

        # Draw text
        if text_color:
            CGContextSetFillColorWithColor(ctx, text_color)
        else:
            CGContextSetFillColorWithColor(ctx, self.create_color(0.1, 0.1, 0.1))

        CGContextSaveGState(ctx)
        Quartz.CGContextSetTextPosition(ctx, rect_x + padding, rect_y + padding + 2)
        CoreText.CTLineDraw(line, ctx)
        CGContextRestoreGState(ctx)

    def draw_title(self, ctx, title: str, subtitle: str):
        """Draw title in the header area."""
        # Title
        title_font = CoreText.CTFontCreateWithName("Helvetica-Bold", 22, None)
        title_attrs = {
            CoreText.kCTFontAttributeName: title_font,
            CoreText.kCTForegroundColorFromContextAttributeName: True,
        }
        title_string = CoreFoundation.CFAttributedStringCreate(None, title, title_attrs)
        title_line = CoreText.CTLineCreateWithAttributedString(title_string)
        title_bounds = CoreText.CTLineGetBoundsWithOptions(title_line, 0)

        CGContextSetFillColorWithColor(ctx, self.create_color(0.15, 0.15, 0.15))
        CGContextSaveGState(ctx)
        title_x = self.width / 2 - title_bounds.size.width / 2
        title_y = self.height - 35
        Quartz.CGContextSetTextPosition(ctx, title_x, title_y)
        CoreText.CTLineDraw(title_line, ctx)
        CGContextRestoreGState(ctx)

        # Subtitle (time)
        subtitle_font = CoreText.CTFontCreateWithName("Helvetica", 16, None)
        subtitle_attrs = {
            CoreText.kCTFontAttributeName: subtitle_font,
            CoreText.kCTForegroundColorFromContextAttributeName: True,
        }
        subtitle_string = CoreFoundation.CFAttributedStringCreate(None, subtitle, subtitle_attrs)
        subtitle_line = CoreText.CTLineCreateWithAttributedString(subtitle_string)
        subtitle_bounds = CoreText.CTLineGetBoundsWithOptions(subtitle_line, 0)

        CGContextSetFillColorWithColor(ctx, self.create_color(0.4, 0.4, 0.4))
        CGContextSaveGState(ctx)
        subtitle_x = self.width / 2 - subtitle_bounds.size.width / 2
        subtitle_y = self.height - 60
        Quartz.CGContextSetTextPosition(ctx, subtitle_x, subtitle_y)
        CoreText.CTLineDraw(subtitle_line, ctx)
        CGContextRestoreGState(ctx)

    def draw_legend(self, ctx):
        """Draw the color legend in the right margin."""
        legend_x = self.width - self.RIGHT_MARGIN + 20
        legend_y = self.map_y + 50
        bar_width = 20
        bar_height = 180

        # Draw legend title
        title_font = CoreText.CTFontCreateWithName("Helvetica-Bold", 11, None)
        title_attrs = {
            CoreText.kCTFontAttributeName: title_font,
            CoreText.kCTForegroundColorFromContextAttributeName: True,
        }

        CGContextSetFillColorWithColor(ctx, self.create_color(0.2, 0.2, 0.2))

        # Title line 1
        title1_string = CoreFoundation.CFAttributedStringCreate(None, "UFP Concentration", title_attrs)
        title1_line = CoreText.CTLineCreateWithAttributedString(title1_string)
        CGContextSaveGState(ctx)
        Quartz.CGContextSetTextPosition(ctx, legend_x - 5, legend_y + bar_height + 35)
        CoreText.CTLineDraw(title1_line, ctx)
        CGContextRestoreGState(ctx)

        # Title line 2
        title2_string = CoreFoundation.CFAttributedStringCreate(None, "(particles/cm³)", title_attrs)
        title2_line = CoreText.CTLineCreateWithAttributedString(title2_string)
        CGContextSaveGState(ctx)
        Quartz.CGContextSetTextPosition(ctx, legend_x + 5, legend_y + bar_height + 20)
        CoreText.CTLineDraw(title2_line, ctx)
        CGContextRestoreGState(ctx)

        # Draw color bar
        for i in range(int(bar_height)):
            value = self.pollution_min + (self.pollution_max - self.pollution_min) * i / bar_height
            color = self.get_plasma_color(value)
            CGContextSetFillColorWithColor(ctx, self.create_color(*color))
            CGContextFillRect(ctx, CGRectMake(legend_x, legend_y + i, bar_width, 1))

        # Draw border
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.3, 0.3, 0.3))
        CGContextSetLineWidth(ctx, 1)
        CGContextAddRect(ctx, CGRectMake(legend_x, legend_y, bar_width, bar_height))
        CGContextStrokePath(ctx)

        # Draw min/max labels
        label_font = CoreText.CTFontCreateWithName("Helvetica", 10, None)
        label_attrs = {
            CoreText.kCTFontAttributeName: label_font,
            CoreText.kCTForegroundColorFromContextAttributeName: True,
        }

        CGContextSetFillColorWithColor(ctx, self.create_color(0.2, 0.2, 0.2))

        # Min label
        min_text = f"{self.pollution_min/1000:.1f}K"
        min_string = CoreFoundation.CFAttributedStringCreate(None, min_text, label_attrs)
        min_line = CoreText.CTLineCreateWithAttributedString(min_string)
        CGContextSaveGState(ctx)
        Quartz.CGContextSetTextPosition(ctx, legend_x + bar_width + 5, legend_y - 2)
        CoreText.CTLineDraw(min_line, ctx)
        CGContextRestoreGState(ctx)

        # Max label
        max_text = f"{self.pollution_max/1000:.1f}K"
        max_string = CoreFoundation.CFAttributedStringCreate(None, max_text, label_attrs)
        max_line = CoreText.CTLineCreateWithAttributedString(max_string)
        CGContextSaveGState(ctx)
        Quartz.CGContextSetTextPosition(ctx, legend_x + bar_width + 5, legend_y + bar_height - 10)
        CoreText.CTLineDraw(max_line, ctx)
        CGContextRestoreGState(ctx)

    def render_frame(self, frame: FrameData) -> bytes:
        """Render a single frame and return PNG data."""
        ctx = CGBitmapContextCreate(
            None,
            self.width, self.height,
            8, self.width * 4,
            self.color_space,
            Quartz.kCGImageAlphaPremultipliedLast
        )

        CGContextSetAllowsAntialiasing(ctx, True)
        CGContextSetShouldAntialias(ctx, True)
        CGContextSetInterpolationQuality(ctx, kCGInterpolationHigh)

        # Draw white background for entire frame
        CGContextSetFillColorWithColor(ctx, self.create_color(0.98, 0.98, 0.98))
        CGContextFillRect(ctx, CGRectMake(0, 0, self.width, self.height))

        # Draw light border around map area
        CGContextSetStrokeColorWithColor(ctx, self.create_color(0.8, 0.8, 0.8))
        CGContextSetLineWidth(ctx, 1)
        CGContextAddRect(ctx, CGRectMake(self.map_x, self.map_y, self.map_width, self.map_height))
        CGContextStrokePath(ctx)

        # Draw base map in the map area
        if self.base_map_image:
            CGContextDrawImage(ctx, CGRectMake(self.map_x, self.map_y, self.map_width, self.map_height),
                             self.base_map_image)
        else:
            # Light gray placeholder
            CGContextSetFillColorWithColor(ctx, self.create_color(0.92, 0.92, 0.92))
            CGContextFillRect(ctx, CGRectMake(self.map_x, self.map_y, self.map_width, self.map_height))

        # Draw wind arrow
        if frame.wind and frame.wind.get('speed_label'):
            wind = frame.wind
            start = self.geo_to_pixel(wind['center_lon'], wind['center_lat'])
            end = self.geo_to_pixel(wind['end_lon'], wind['end_lat'])

            # Arrow line
            dark_blue = self.create_color(0.1, 0.2, 0.6, 0.9)
            CGContextSetStrokeColorWithColor(ctx, dark_blue)
            CGContextSetLineWidth(ctx, 5)
            CGContextSetLineCap(ctx, kCGLineCapRound)
            CGContextMoveToPoint(ctx, start[0], start[1])
            CGContextAddLineToPoint(ctx, end[0], end[1])
            CGContextStrokePath(ctx)

            # Arrowhead
            angle = math.atan2(end[1] - start[1], end[0] - start[0])
            arrow_length = 18
            arrow_angle = math.pi / 6

            p1 = (
                end[0] - arrow_length * math.cos(angle - arrow_angle),
                end[1] - arrow_length * math.sin(angle - arrow_angle)
            )
            p2 = (
                end[0] - arrow_length * math.cos(angle + arrow_angle),
                end[1] - arrow_length * math.sin(angle + arrow_angle)
            )

            CGContextSetFillColorWithColor(ctx, dark_blue)
            CGContextMoveToPoint(ctx, end[0], end[1])
            CGContextAddLineToPoint(ctx, p1[0], p1[1])
            CGContextAddLineToPoint(ctx, p2[0], p2[1])
            CGContextFillPath(ctx)

            # Center point
            CGContextSetFillColorWithColor(ctx, self.create_color(1, 1, 1))
            CGContextSetStrokeColorWithColor(ctx, dark_blue)
            CGContextSetLineWidth(ctx, 3)
            CGContextAddEllipseInRect(ctx, CGRectMake(start[0] - 10, start[1] - 10, 20, 20))
            CGContextDrawPath(ctx, kCGPathFillStroke)

            # Wind speed label
            self.draw_label(
                ctx, wind['speed_label'],
                start[0], start[1] + 35,
                font_size=12, bold=True,
                bg_color=self.create_color(0.85, 0.92, 0.98, 0.95)
            )

        # Draw pollution circles and labels
        for sensor in frame.sensors:
            lon, lat, pollution, label = sensor
            pos = self.geo_to_pixel(lon, lat)
            size = self.get_circle_size(pollution)
            color = self.get_plasma_color(pollution)

            # Draw circle with border
            CGContextSetFillColorWithColor(ctx, self.create_color(*color, 0.75))
            CGContextAddEllipseInRect(ctx, CGRectMake(pos[0] - size/2, pos[1] - size/2, size, size))
            CGContextFillPath(ctx)

            # Circle border
            CGContextSetStrokeColorWithColor(ctx, self.create_color(*color, 1.0))
            CGContextSetLineWidth(ctx, 2)
            CGContextAddEllipseInRect(ctx, CGRectMake(pos[0] - size/2, pos[1] - size/2, size, size))
            CGContextStrokePath(ctx)

            # Pollution label - positioned above circle with nice styling
            self.draw_label(
                ctx, label,
                pos[0], pos[1] + size/2 + 18,
                font_size=12, bold=True,
                bg_color=self.create_color(1, 1, 1, 0.95),
                shadow=True
            )

        # Draw title in header area
        self.draw_title(ctx, f"Ultrafine Particle Concentration — {frame.title_date}",
                       f"Time: {frame.time_label}")

        # Draw legend in right margin
        self.draw_legend(ctx)

        return CGBitmapContextCreateImage(ctx)

    def save_image(self, image, path: str):
        """Save CGImage to PNG file."""
        url = NSURL.fileURLWithPath_(path)
        dest = CGImageDestinationCreateWithURL(url, "public.png", 1, None)
        CGImageDestinationAddImage(dest, image, None)
        CGImageDestinationFinalize(dest)

    def render_all_frames(self, frames: list[FrameData], output_dir: str, num_workers: int = 8):
        """Render all frames in parallel."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        total = len(frames)
        print(f"\nRendering {total} frames with Metal GPU...")

        start_time = time.time()
        completed = [0]

        def render_one(frame):
            image = self.render_frame(frame)
            output_file = output_path / f"frame_{frame.frame_number:04d}.png"
            self.save_image(image, str(output_file))
            completed[0] += 1
            progress = (completed[0] * 100) // total
            print(f"\rProgress: {progress}% ({completed[0]}/{total} frames)", end="", flush=True)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            list(executor.map(render_one, frames))

        elapsed = time.time() - start_time
        print(f"\n\nRendering complete!")
        print(f"  Total time: {elapsed:.1f} seconds")
        print(f"  Average: {elapsed/total:.3f} seconds per frame")
        print(f"  Throughput: {total/elapsed*60:.1f} frames per minute")
