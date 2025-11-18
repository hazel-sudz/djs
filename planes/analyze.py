import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from collections import defaultdict

"""
data format: 
 "timestamp":1754017201000,
    "icao24":"aa56b5",
    "latitude":39.2513122559,
    "longitude":-89.1027633004,
    "groundspeed":513.0,
    "track":65.5837824029,
    "vertical_rate":0.0,
    "callsign":"UAL2439",
    "onground":false,
    "alert":false,
    "spi":false,
    "squawk":"4065",
    "altitude":37000.0,
    "geoaltitude":39075.0,
    "last_position":1754017198.5750000477,
    "lastcontact":1754017200.8369998932,
    "serials":[
      -1408234602,
      -1408131058,
      -1408232033,
      -1408223638,
      -1408230429
    ],
    "hour":1754017200000
  },
"""

def get_data_by_callsign():
    current_folder = Path(__file__).parent
    data_folder = current_folder.joinpath("data")

    # load all data for a given day and merge by callsign
    all_data = {}

    august_first = data_folder.joinpath("2025-08-01")
    for day_data in august_first.iterdir():
        for files in day_data.iterdir():
            if "json" in files.name:
                 data = json.loads(files.read_text())

                 for entry in data:
                    callsign = entry["callsign"]
                    if callsign not in all_data:
                        all_data[callsign] = []

                    all_data[callsign].append(entry)
    
    # Sort all entries by timestamp for each callsign
    for callsign in all_data:
        all_data[callsign].sort(key=lambda x: x["timestamp"])
    
    # Determine takeoff and landing times for each callsign
    # Takeoff is defined as first moment when altitude reaches 10,000 ft
    # Landing is defined as last moment when altitude is >= 10,000 ft (before descending below)
    takeoff_threshold = 10000  # feet
    takeoff_times = {}
    landing_times = {}
    
    for callsign, entries in all_data.items():
        takeoff_time = None
        landing_time = None
        
        # Find takeoff (first time altitude >= threshold)
        for entry in entries:
            altitude = entry.get("altitude", 0)
            if altitude is not None and altitude >= takeoff_threshold:
                takeoff_time = entry["timestamp"]
                break
        
        # Find landing (last time altitude >= threshold, after takeoff)
        if takeoff_time is not None:
            # Iterate backwards from the end to find the last time above threshold
            for entry in reversed(entries):
                altitude = entry.get("altitude", 0)
                if altitude is not None and altitude >= takeoff_threshold:
                    # Make sure landing is after takeoff
                    if entry["timestamp"] > takeoff_time:
                        landing_time = entry["timestamp"]
                    break
        
        # Only store if both takeoff and landing are found
        if takeoff_time is not None and landing_time is not None:
            takeoff_times[callsign] = takeoff_time
            landing_times[callsign] = landing_time
    
    print(f"Found {len(takeoff_times)} callsigns with both takeoff and landing")
    print(f"  (Filtered out callsigns that only had takeoff or only had landing)")
    
    # Bin takeoff times by minute
    # Convert timestamps to datetime and round to nearest minute
    takeoff_datetimes = [datetime.fromtimestamp(ts / 1000) for ts in takeoff_times]
    
    # Create minute bins (round down to the minute)
    minute_bins = defaultdict(int)
    for dt in takeoff_datetimes:
        # Round down to the minute (remove seconds and microseconds)
        minute_key = dt.replace(second=0, microsecond=0)
        minute_bins[minute_key] += 1
    
    # Sort by time for plotting
    sorted_minutes = sorted(minute_bins.keys())
    takeoff_counts = [minute_bins[minute] for minute in sorted_minutes]
    
    # Create the plot - using bar plot since we have discrete time bins
    plt.figure(figsize=(14, 6))
    # Use timedelta for bar width (1 minute)
    bar_width = timedelta(minutes=1)
    plt.bar(sorted_minutes, takeoff_counts, width=bar_width, align='edge', alpha=0.7, color='steelblue')
    plt.xlabel('Time', fontsize=12)
    plt.ylabel('Number of Takeoffs', fontsize=12)
    plt.title(f'Takeoff Count per Minute (Takeoff = Altitude ≥ {takeoff_threshold:,} ft)', 
              fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save the plot
    output_path = current_folder.joinpath("takeoff_count_plot.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {output_path}")
    
    # Print statistics
    print(f"\nTakeoff Statistics:")
    print(f"  Total takeoffs detected: {len(takeoff_times)}")
    print(f"  Time range: {sorted_minutes[0]} to {sorted_minutes[-1]}")
    print(f"  Max takeoffs in a single minute: {max(takeoff_counts)}")
    print(f"  Average takeoffs per minute: {sum(takeoff_counts)/len(takeoff_counts):.2f}")
    
    plt.show()


if __name__ == '__main__':
    get_data_by_callsign()