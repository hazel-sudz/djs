#!/usr/bin/env python3
"""
Fetch arrivals and departures from BOS (Boston Logan Intl)
using the traffic library and OpenSky's Trino institutional interface.

Creates folder structure:
    data/YYYY-MM-DD/HH-MM/
Each file inside corresponds to a single aircraft's ADS-B track in that hour.
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

# Define one-hour window (you can replace these with now() logic)
start = datetime(2025, 8, 1, 0, 0)
stop = start + timedelta(hours=1)

# --- Query OpenSky ---
traffic = opensky.history(
    start=start.strftime("%Y-%m-%d %H:%M"),
    stop=stop.strftime("%Y-%m-%d %H:%M"),
    airport=airport,
    return_flight=False,
    cached=True,
    compress=True,
    limit=None,
)

print(f"Fetched {len(traffic)} flights from {start} to {stop}")

# --- Create folder structure ---
day_folder = start.strftime("data/%Y-%m-%d")
hour_folder = os.path.join(day_folder, f"{start.strftime('%H')}-{stop.strftime('%H')}")
os.makedirs(hour_folder, exist_ok=True)

# --- Loop over flights ---
for f in traffic:
    callsign = (f.callsign or f.icao24 or "UNKNOWN").strip()
    safe_name = callsign.replace("/", "_").replace(" ", "_")

    if f.data is None or f.data.empty:
        print(f"Skipping {callsign}: no data")
        continue

    # Save CSV
    csv_path = os.path.join(hour_folder, f"{safe_name}.csv")
    f.data.to_csv(csv_path, index=False)

    # Save JSON (human-readable)
    json_path = os.path.join(hour_folder, f"{safe_name}.json")
    f.data.to_json(json_path, orient="records", indent=2)

    print(f"Saved {callsign} → {csv_path}")

print(f"✅ All done! Data saved in: {hour_folder}")
