# UFP Animation Pipeline

Renders ultrafine particle (UFP) pollution data as an animated video with map visualization.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- macOS (uses Quartz/CoreGraphics for GPU-accelerated rendering)
- ffmpeg (for video encoding)

## Setup

1. Install uv if not already installed:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Install ffmpeg:
   ```bash
   brew install ffmpeg
   ```

3. Place your data file at `data/Eastie_UFP.rds`

## Generate Video

Run from the `animation` directory:

```bash
cd animation
uv run python render_simple.py
```

This will:
- Process all available days in the dataset
- Render frames with pollution circles and wind arrows
- Create a combined video at `out_simple/animation.mp4`

## Options

```bash
# Render specific days only
uv run python render_simple.py --days 2025-08-01 2025-08-02

# Custom output directory
uv run python render_simple.py --output my_output

# Adjust frame rate (default: 2 fps)
uv run python render_simple.py --fps 4

# Custom resolution (default: 1800x1200)
uv run python render_simple.py --width 1920 --height 1080

# Custom data file path
uv run python render_simple.py --data /path/to/data.rds
```

## Output

- `out_simple/animation.mp4` - Combined video of all days
- `out_simple/frames/` - Individual PNG frames
- `out_simple/base_map.png` - OpenStreetMap base layer
