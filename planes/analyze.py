import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime

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
    
    # Select UAL2439 callsign
    target_callsign = "UAL2439"
    if target_callsign not in all_data:
        print(f"Warning: {target_callsign} not found in data")
        return
    
    ual2439_data = all_data[target_callsign]
    
    # Extract timestamps and altitudes
    timestamps = [entry["timestamp"] for entry in ual2439_data]
    altitudes = [entry["altitude"] for entry in ual2439_data]
    
    # Convert timestamps to datetime for better plotting
    datetime_objects = [datetime.fromtimestamp(ts / 1000) for ts in timestamps]
    
    # Create the plot
    plt.figure(figsize=(12, 6))
    plt.plot(datetime_objects, altitudes, 'b-', linewidth=1.5)
    plt.xlabel('Time', fontsize=12)
    plt.ylabel('Altitude (feet)', fontsize=12)
    plt.title(f'Altitude vs Time for {target_callsign}', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save the plot
    output_path = current_folder.joinpath(f"{target_callsign}_altitude_plot.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {output_path}")
    
    # Also show basic statistics
    print(f"\nData summary for {target_callsign}:")
    print(f"  Total data points: {len(ual2439_data)}")
    print(f"  Time range: {datetime_objects[0]} to {datetime_objects[-1]}")
    print(f"  Altitude range: {min(altitudes):.0f} to {max(altitudes):.0f} feet")
    print(f"  Mean altitude: {sum(altitudes)/len(altitudes):.0f} feet")
    
    plt.show()


if __name__ == '__main__':
    get_data_by_callsign()