# East Boston Air Quality Analysis

Analysis of ultrafine particle (UFP) pollution in East Boston, with visualization tools for sensor data and flight tracking.

## Projects

### animation/
Renders UFP sensor data as animated videos showing pollution levels over time.

```bash
cd animation
uv run python render.py
```

See [animation/README.md](animation/README.md) for details.

### planes/
Flight tracking and analysis tools for correlating aircraft activity with pollution data.

### docs/
Data documentation and analysis summaries.

## Data

UFP sensor data is stored in `animation/data/Eastie_UFP.rds` (R data format).
