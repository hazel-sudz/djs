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

flight = opensky.history(
    "2017-02-05 15:45",
    stop="2017-02-05 16:45",
    callsign="EZY158T",
    # returns a Flight instead of a Traffic
    return_flight=True
)
print(flight)