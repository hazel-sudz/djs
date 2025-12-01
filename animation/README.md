# UFP Animation

Renders ultrafine particle (UFP) pollution data as an animated video with map visualization.

## Requirements

- macOS (uses Quartz/CoreGraphics for GPU-accelerated rendering)
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- ffmpeg

## Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install ffmpeg
brew install ffmpeg

# Place data file
cp /path/to/Eastie_UFP.rds data/
```

## Generate Video

```bash
uv run python render.py
```

Output: `output/animation.mp4`

## Options

```bash
# Specific days only
uv run python render.py --days 2025-08-01 2025-08-02

# Adjust frame rate (default: 2 fps)
uv run python render.py --fps 4

# Custom resolution (default: 1800x1200)
uv run python render.py --width 1920 --height 1080
```
