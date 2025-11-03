#!/usr/bin/env python3
"""
Fetches arrivals and departures from BOS (Boston Logan Intl)
using the traffic library and OpenSky's Trino institutional interface.
"""

from traffic.data import opensky
import pandas as pd
import os
from datetime import datetime, timedelta

from traffic.data import opensky

airport = "KBOS"

username = os.environ['OPENSKY_USERNAME']
password = os.environ['OPENSKY_PASSWORD']

flight = opensky.history(
    start="2025-08-01 00:00",
    stop="2025-08-01 01:00",
    airport=airport,
    # returns a Flight instead of a Traffic
    return_flight=False,
    cached=True,
    compress=True,
    limit=None,

)
print(flight)

print(type(flight))
print(len(flight))
print(flight.data.head())

for f in flight:
    print(f.callsign, f.start, f.stop)
