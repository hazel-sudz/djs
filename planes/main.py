#!/usr/bin/env python3
"""
Fetch arrivals and departures from BOS (Boston Logan Intl)
using the traffic library and OpenSky's Trino institutional interface.

Loops hourly from 2025-08-01 to 2025-08-13, creating folder structure:
    data/YYYY-MM-DD/HH-HH/
Each file corresponds to one aircraft's ADS-B track for that hour.
"""

import os
import json
from datetime import datetime, timedelta
import pandas as pd
from traffic.data import opensky

# --- Configuration ---
airport = "KBOS"
username = os.environ["OPENSKY_USERNAME"]
password = os.environ["OPENSKY_PASSWORD"]

start_date = datetime(2025, 8, 1, 0, 0)
end_date   = datetime(2025, 8, 13, 0, 0)

# --- Loop through every hour ---
current = start_date
while current < end_date:
    next_hour = current + timedelta(hours=1)

    print(f"\n=== Fetching flights from {current} to {next_hour} ===")

    try:
        traffic = opensky.history(
            start=current.strftime("%Y-%m-%d %H:%M"),
            stop=next_hour.strftime("%Y-%m-%d %H:%M"),
            airport=airport,
            return_flight=False,
            cached=True,
            compress=True,
            limit=None,
        )
    except Exception as e:
        print(f"⚠️ Error fetching {current}: {e}")
        current = next_hour
        continue

    print(f"Fetched {len(traffic)} flights.")

    # --- Create folder structure ---
    day_folder = current.strftime("data/%Y-%m-%d")
    hour_folder = os.path.join(day_folder, f"{current.strftime('%H')}-{next_hour.strftime('%H')}")
    os.makedirs(hour_folder, exist_ok=True)

    # --- Loop over flights ---
    for f in traffic:
        callsign = (f.callsign or f.icao24 or "UNKNOWN").strip()
        safe_name = callsign.replace("/", "_").replace(" ", "_")

        if f.data is None or f.data.empty:
            print(f"Skipping {callsign}: no data")
            continue

        # --- Save raw data ---
        csv_path = os.path.join(hour_folder, f"{safe_name}.csv")
        f.data.to_csv(csv_path, index=False)

        json_path = os.path.join(hour_folder, f"{safe_name}.json")
        f.data.to_json(json_path, orient="records", indent=2)

        print(f"Saved {callsign} → {csv_path}")

    current = next_hour  # move to next hour

print("\n✅ All done! Data saved in ./data/")
