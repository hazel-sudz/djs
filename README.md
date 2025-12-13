# East Boston Air Quality Analysis

Analysis of ultrafine particle (UFP) pollution in East Boston, with visualization tools for sensor data and flight tracking.

## Rendered Animations

Animated visualizations of UFP pollution data are available on Google Drive:

**[View All Animations on Google Drive](https://drive.google.com/drive/folders/1gRxsAv3I6MOy5SUtnhu3RXpZoXTXRl3K?usp=sharing)**

### East Boston UFP Animation

[![East Boston UFP Animation](docs/images/eastie_thumbnail.png)](https://drive.google.com/drive/folders/1gRxsAv3I6MOy5SUtnhu3RXpZoXTXRl3K?usp=sharing)

*Click the image above to view the animation. Shows UFP (ultrafine particle) concentrations across East Boston over time, with data interpolated from sensor measurements using Gaussian smoothing.*

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
