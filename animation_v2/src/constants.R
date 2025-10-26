
# Define sensor coordinates (lat, lon)
sensor_coords <- data.frame(
  sensor = c("MOD-UFP-00007", "MOD-UFP-00008", "MOD-UFP-00009"),
  lat = c(42.36148, 42.38407, 42.36407),
  lon = c(-70.97251, -71.00227, -71.0291),
  stringsAsFactors = FALSE
)

# Calculate map extent from sensor coordinates with proper centering and padding
lat_center <- mean(sensor_coords$lat)
lon_center <- mean(sensor_coords$lon)
lat_range <- max(sensor_coords$lat) - min(sensor_coords$lat)
lon_range <- max(sensor_coords$lon) - min(sensor_coords$lon)

# Add padding (20% of the range or minimum 0.01 degrees)
lat_padding <- max(0.01, lat_range * 0.2)
lon_padding <- max(0.01, lon_range * 0.2)

lat_min <- lat_center - lat_range/2 - lat_padding
lat_max <- lat_center + lat_range/2 + lat_padding
lon_min <- lon_center - lon_range/2 - lon_padding
lon_max <- lon_center + lon_range/2 + lon_padding

# Print calculated coordinates for debugging
cat("Sensor coordinates:\n")
print(sensor_coords)
cat("\nCalculated map extent:\n")
cat("Latitude range:", lat_min, "to", lat_max, "\n")
cat("Longitude range:", lon_min, "to", lon_max, "\n")
cat("Center point:", lat_center, ",", lon_center, "\n\n")

