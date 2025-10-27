# Airplane Flight Data API Functions for Boston Logan Airport (BOS)
# This module provides functions to fetch airplane takeoff times for correlation with pollution data
# Uses OpenSky Network API (free, no API key required)

library(httr)
library(jsonlite)
library(dplyr)
library(lubridate)

# Configuration
BOS_AIRPORT_CODE <- "KBOS"  # ICAO code for Boston Logan

# OpenSky Network API (Free tier - no API key required)
# Documentation: https://opensky-network.org/apidoc/
OPENSKY_BASE_URL <- "https://opensky-network.org/api"

#' Get airplane departures from BOS using OpenSky Network API
#' 
#' @param date Date in YYYY-MM-DD format
#' @param start_time Start time in HH:MM format (24-hour)
#' @param end_time End time in HH:MM format (24-hour)
#' @return Data frame with departure information
get_bos_departures_opensky <- function(date, start_time = "00:00", end_time = "23:59") {
  
  # Convert date and times to Unix timestamps
  start_datetime <- as.POSIXct(paste(date, start_time), tz = "UTC")
  end_datetime <- as.POSIXct(paste(date, end_time), tz = "UTC")
  
  start_timestamp <- as.numeric(start_datetime)
  end_timestamp <- as.numeric(end_datetime)
  
  # OpenSky API endpoint for flights
  url <- paste0(OPENSKY_BASE_URL, "/flights/all")
  
  # Make API request
  response <- GET(url, query = list(
    airport = BOS_AIRPORT_CODE,
    begin = start_timestamp,
    end = end_timestamp
  ))
  
  if (status_code(response) != 200) {
    warning(paste("OpenSky API request failed with status:", status_code(response)))
    return(data.frame())
  }
  
  # Parse JSON response
  data <- content(response, "text", encoding = "UTF-8")
  flights <- fromJSON(data)
  
  if (length(flights) == 0) {
    cat("No departure data found for", date, "\n")
    return(data.frame())
  }
  
  # Convert to data frame and clean up
  flights_df <- as.data.frame(flights)
  
  # Add readable timestamps
  flights_df$departure_time_readable <- as.POSIXct(flights_df$firstSeen, origin = "1970-01-01", tz = "UTC")
  flights_df$departure_time_local <- with_tz(flights_df$departure_time_readable, "America/New_York")
  
  # Filter and select relevant columns
  result <- flights_df %>%
    select(
      icao24 = icao24,
      callsign = callsign,
      departure_time_utc = firstSeen,
      departure_time_readable,
      departure_time_local,
      origin = estDepartureAirport,
      destination = estArrivalAirport
    ) %>%
    filter(!is.na(callsign) & callsign != "") %>%
    arrange(departure_time_local)
  
  cat("Found", nrow(result), "departures from BOS on", date, "\n")
  return(result)
}


#' Get airplane departures from BOS using OpenSky Network API
#' 
#' @param date Date in YYYY-MM-DD format
#' @param start_time Start time in HH:MM format (24-hour)
#' @param end_time End time in HH:MM format (24-hour)
#' @return Data frame with departure information
get_bos_departures <- function(date, start_time = "00:00", end_time = "23:59") {
  
  cat("Fetching departure data for", date, "from", start_time, "to", end_time, "\n")
  
  # Use OpenSky API
  departures <- get_bos_departures_opensky(date, start_time, end_time)
  
  if (nrow(departures) == 0) {
    warning("No departure data found for the specified date and time range")
  }
  
  return(departures)
}

#' Filter departures by time window for correlation analysis
#' 
#' @param departures Data frame from get_bos_departures()
#' @param start_time Start time in HH:MM format (24-hour)
#' @param end_time End time in HH:MM format (24-hour)
#' @return Filtered data frame
filter_departures_by_time <- function(departures, start_time, end_time) {
  
  if (nrow(departures) == 0) {
    return(departures)
  }
  
  # Parse times
  start_hour <- as.numeric(strsplit(start_time, ":")[[1]][1])
  start_min <- as.numeric(strsplit(start_time, ":")[[1]][2])
  end_hour <- as.numeric(strsplit(end_time, ":")[[1]][1])
  end_min <- as.numeric(strsplit(end_time, ":")[[1]][2])
  
  # Filter by time
  filtered <- departures %>%
    mutate(
      hour = hour(departure_time_local),
      minute = minute(departure_time_local)
    ) %>%
    filter(
      (hour > start_hour) | (hour == start_hour & minute >= start_min),
      (hour < end_hour) | (hour == end_hour & minute <= end_min)
    ) %>%
    select(-hour, -minute)
  
  cat("Filtered to", nrow(filtered), "departures between", start_time, "and", end_time, "\n")
  return(filtered)
}

#' Get departure summary statistics
#' 
#' @param departures Data frame from get_bos_departures()
#' @return Summary statistics
get_departure_summary <- function(departures) {
  
  if (nrow(departures) == 0) {
    return(list(
      total_departures = 0,
      time_range = "No data",
      peak_hour = "No data",
      avg_departures_per_hour = 0
    ))
  }
  
  # Calculate statistics
  total_departures <- nrow(departures)
  time_range <- paste(
    format(min(departures$departure_time_local), "%H:%M"),
    "to",
    format(max(departures$departure_time_local), "%H:%M")
  )
  
  # Find peak hour
  hourly_counts <- departures %>%
    mutate(hour = hour(departure_time_local)) %>%
    count(hour) %>%
    arrange(desc(n))
  
  peak_hour <- if (nrow(hourly_counts) > 0) {
    paste(hourly_counts$hour[1], ":00", sep = "")
  } else {
    "No data"
  }
  
  # Calculate average departures per hour
  hours_span <- as.numeric(difftime(
    max(departures$departure_time_local),
    min(departures$departure_time_local),
    units = "hours"
  ))
  
  avg_per_hour <- if (hours_span > 0) {
    round(total_departures / hours_span, 1)
  } else {
    0
  }
  
  return(list(
    total_departures = total_departures,
    time_range = time_range,
    peak_hour = peak_hour,
    avg_departures_per_hour = avg_per_hour
  ))
}
