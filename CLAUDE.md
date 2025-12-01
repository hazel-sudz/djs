# Claude Instructions

## Project Overview
East Boston air quality analysis project with UFP (ultrafine particle) pollution visualization.

## Key Directories
- `animation/` - Python rendering pipeline for UFP data visualization
- `planes/` - Flight tracking analysis
- `docs/` - Data documentation

## Animation Pipeline

### Running
```bash
cd animation
uv run python render.py
```

### Key Files
- `render.py` - Main entry point
- `renderer.py` - GPU rendering (macOS Quartz/CoreGraphics)
- `processing.py` - Data processing with Gaussian smoothing
- `config.py` - Map extent and sensor coordinates
- `data/Eastie_UFP.rds` - Source data (R format)

### Output
- `output/animation.mp4` - Combined video of all days
- `output/frames/` - Individual PNG frames

## Dependencies
- Use `uv` for Python package management (not pip directly)
- macOS required for Quartz rendering
- ffmpeg required for video encoding

## Common Tasks

### Regenerate video
```bash
cd animation && uv run python render.py
```

### Render specific days
```bash
uv run python render.py --days 2025-08-01 2025-08-02
```

### Restore data file if deleted
```bash
git show cb70c5f6:animation/data/Eastie_UFP.rds > animation/data/Eastie_UFP.rds
```
