# Load required packages
library(openair)
library(dplyr)
library(lubridate)

# Load the Eastie_UFP.rds data
cat("Loading Eastie_UFP.rds data...\n")
eastie_data <- readRDS("Eastie_UFP.rds")


# Check unique sensor names
cat("\nUnique sensor names:\n")
unique_sensors <- unique(eastie_data$sn.x)
print(unique_sensors[!is.na(unique_sensors)])

# Count observations by sensor
cat("\nCount by sensor:\n")
sensor_counts <- table(eastie_data$sn.x, useNA = "ifany")
print(sensor_counts)

# Split data by sensor name
cat("\nSplitting data by sensor...\n")
sensor_data <- split(eastie_data, eastie_data$sn.x)

# Display information about each sensor dataset
for(sensor_name in names(sensor_data)) {
  if(!is.na(sensor_name)) {
    cat("\n=== Sensor:", sensor_name, "===\n")
    cat("Number of observations:", nrow(sensor_data[[sensor_name]]), "\n")
    cat("Date range:", as.character(min(sensor_data[[sensor_name]]$timestamp)), "to", as.character(max(sensor_data[[sensor_name]]$timestamp)), "\n")
    cat("Pollution range:", min(sensor_data[[sensor_name]]$cpc_particle_number_conc_corr.x, na.rm = TRUE), "to", max(sensor_data[[sensor_name]]$cpc_particle_number_conc_corr.x, na.rm = TRUE), "particles/cm³\n")
  }
}

# Create individual data frames for each sensor
sensor_00007 <- sensor_data[["MOD-UFP-00007"]]
sensor_00008 <- sensor_data[["MOD-UFP-00008"]] 
sensor_00009 <- sensor_data[["MOD-UFP-00009"]]

cat("\nData split complete! Individual sensor datasets created:\n")
cat("- sensor_00007:", nrow(sensor_00007), "observations\n")
cat("- sensor_00008:", nrow(sensor_00008), "observations\n") 
cat("- sensor_00009:", nrow(sensor_00009), "observations\n")