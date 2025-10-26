# Airplane Flight Data API for Pollution Correlation

This document describes the airplane flight data API implemented in `src/planes.R` for correlating airplane takeoff times from Boston Logan Airport (BOS) with pollution sensor data.

## API Used

### OpenSky Network API
- **URL**: https://opensky-network.org/
- **Cost**: Free (no API key required)
- **Data Coverage**: Real-time and limited historical data
- **Rate Limits**: 10 requests per minute
- **Best For**: Recent data (last few days to weeks)

**Pros:**
- Completely free
- No registration required
- Good for real-time data
- Reliable service
- No API key needed

**Cons:**
- Limited historical data
- Rate limited (10 requests per minute)
- Less detailed flight information than commercial APIs

## Setup Instructions

### 1. Install Required Packages
The required packages are automatically installed when you run `src/setup.R`:
- `httr` - For API requests
- `jsonlite` - For JSON parsing
- `dplyr` - For data manipulation
- `lubridate` - For date/time handling

### 2. No API Key Required
The OpenSky Network API is completely free and requires no registration or API key.

## Usage Examples

### Basic Usage
```r
# Load the modules
source("src/setup.R")
source("src/planes.R")

# Get departures for a specific date
departures <- get_bos_departures("2024-01-15")

# Get departures for a specific time window
morning_departures <- get_bos_departures("2024-01-15", "06:00", "12:00")
```

### Advanced Usage
```r
# Get departure data
departures <- get_bos_departures("2024-01-15")

# Filter by time window
morning_departures <- filter_departures_by_time(departures, "06:00", "10:00")

# Get summary statistics
summary_stats <- get_departure_summary(departures)
print(summary_stats)

# Run full correlation analysis
result <- correlate_airplanes_pollution("2024-01-15")
```

## Data Structure

### Departure Data Frame
The functions return a data frame with the following columns:

**OpenSky API Data Structure:**
- `icao24`: Aircraft identifier
- `callsign`: Flight number/callsign
- `departure_time_utc`: UTC timestamp
- `departure_time_readable`: Human-readable UTC time
- `departure_time_local`: Local time (America/New_York)
- `origin`: Departure airport (should be KBOS)
- `destination`: Arrival airport

## Correlation with Pollution Data

### Time Windows
The system creates 30-minute windows around each departure:
- 15 minutes before takeoff
- 15 minutes after takeoff

### Integration Steps
1. Fetch airplane departure data for your analysis date
2. Create time windows around each departure
3. Filter your pollution sensor data by these time windows
4. Calculate correlation statistics
5. Visualize pollution spikes vs departure times

### Example Integration
```r
# Get airplane data
airplane_data <- correlate_airplanes_pollution("2024-01-15")

# Filter pollution data by time windows
pollution_during_departures <- filter_pollution_by_windows(
  pollution_data, 
  airplane_data$time_windows
)

# Calculate correlations
correlation_results <- calculate_pollution_correlation(
  pollution_during_departures, 
  airplane_data$departures
)
```

## Troubleshooting

### Common Issues

1. **No data returned**
   - Check if the date is too far in the past (OpenSky has limited historical data)
   - Verify the date format (YYYY-MM-DD)
   - Check your internet connection

2. **API rate limiting**
   - OpenSky: 10 requests per minute
   - Add delays between requests if needed

### Error Messages
- `"OpenSky API request failed"`: Network or API issue
- `"No departure data found"`: No flights on the specified date

## Best Practices

1. **Data Caching**: Cache API responses to avoid repeated requests
2. **Error Handling**: Always check for empty results
3. **Time Zones**: Be aware of UTC vs local time conversions
4. **Rate Limiting**: Respect API rate limits
5. **Data Validation**: Verify data quality before correlation analysis

## File Structure

```
animation_v2/
├── src/
│   ├── planes.R                    # Main airplane API functions
│   ├── setup.R                     # Package installation and loading
│   └── constants.R                 # Sensor coordinates and constants
├── example_airplane_correlation.R  # Example usage and correlation
└── README_airplane_apis.md        # This documentation
```

## Support

For issues with:
- **OpenSky API**: Visit https://opensky-network.org/
- **R Code**: Check the example files and function documentation
