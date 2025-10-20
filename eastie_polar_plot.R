# Script to create polar plot for Ultrafine Particle (UFP) data from Eastie_UFP.rds
# Author: Generated for air quality analysis
# Date: 2025

# Load required packages
library(openair)
library(dplyr)
library(lubridate)

# Load the Eastie_UFP.rds data
cat("Loading Eastie_UFP.rds data...\n")
eastie_data <- readRDS("Eastie_UFP.rds")

# Display basic information about the data
cat("Data structure:\n")
str(eastie_data)

cat("\nColumn names:\n")
colnames(eastie_data)

cat("\nFirst few rows:\n")
head(eastie_data)

# Check for UFP particle concentration columns
ufp_cols <- c("cpc_particle_number_conc_corr.x", "cpc_particle_number_conc_corr.y")
available_ufp_cols <- ufp_cols[ufp_cols %in% colnames(eastie_data)]

if(length(available_ufp_cols) > 0) {
  cat("\nUFP particle concentration columns found:", paste(available_ufp_cols, collapse = ", "), "\n")
  
  # Check for wind direction and wind speed columns
  wind_dir_cols <- c("wd", "met.wx_wd", "met_wx_wd")
  wind_speed_cols <- c("ws", "met.wx_ws", "met_wx_ws")
  
  available_wd_cols <- wind_dir_cols[wind_dir_cols %in% colnames(eastie_data)]
  available_ws_cols <- wind_speed_cols[wind_speed_cols %in% colnames(eastie_data)]
  
  if(length(available_wd_cols) > 0 && length(available_ws_cols) > 0) {
    cat("Wind direction columns found:", paste(available_wd_cols, collapse = ", "), "\n")
    cat("Wind speed columns found:", paste(available_ws_cols, collapse = ", "), "\n")
    
    # Use the first available wind columns for polar plots
    wd_col <- available_wd_cols[1]
    ws_col <- available_ws_cols[1]
    ufp_col <- available_ufp_cols[1]
    
    cat("Using wind direction column:", wd_col, "\n")
    cat("Using wind speed column:", ws_col, "\n")
    cat("Using UFP concentration column:", ufp_col, "\n")
    
    # Data quality checks before creating polar plots
    cat("Performing data quality checks...\n")
    
    # Check for valid wind direction and speed data
    valid_wd <- !is.na(eastie_data[[wd_col]]) & eastie_data[[wd_col]] >= 0 & eastie_data[[wd_col]] <= 360
    valid_ws <- !is.na(eastie_data[[ws_col]]) & eastie_data[[ws_col]] >= 0
    valid_ufp <- !is.na(eastie_data[[ufp_col]]) & eastie_data[[ufp_col]] > 0
    
    cat("Valid wind direction observations:", sum(valid_wd), "\n")
    cat("Valid wind speed observations:", sum(valid_ws), "\n")
    cat("Valid UFP concentration observations:", sum(valid_ufp), "\n")
    
    # Create subset with valid data
    valid_data <- eastie_data[valid_wd & valid_ws & valid_ufp, ]
    cat("Valid observations for polar plot:", nrow(valid_data), "\n")
    
    if(nrow(valid_data) < 100) {
      cat("Warning: Not enough valid data points for polar plot. Need at least 100 observations.\n")
      cat("Consider using a different statistic or reducing the smoothing parameter.\n")
    }
    
    # Create polar plot for UFP concentrations
    cat("Creating polar plot for UFP concentrations...\n")
    
    # Basic polar plot with reduced smoothing parameter
    tryCatch({
      polar_plot <- polarPlot(valid_data, 
                             pollutant = ufp_col,
                             k = 50,  # Reduced smoothing parameter
                             main = "Polar Plot: Ultrafine Particle Concentrations")
      print(polar_plot)
    }, error = function(e) {
      cat("Error creating basic polar plot:", e$message, "\n")
      cat("Trying with even lower smoothing parameter...\n")
      
      tryCatch({
        polar_plot <- polarPlot(valid_data, 
                               pollutant = ufp_col,
                               k = 25,  # Even lower smoothing parameter
                               main = "Polar Plot: Ultrafine Particle Concentrations")
        print(polar_plot)
      }, error = function(e2) {
        cat("Still failing. Trying with nwr statistic...\n")
        
        tryCatch({
          polar_plot <- polarPlot(valid_data, 
                                 pollutant = ufp_col,
                                 statistic = "nwr",
                                 main = "Polar Plot: Ultrafine Particle Concentrations")
          print(polar_plot)
        }, error = function(e3) {
          cat("All polar plot attempts failed. Check your data quality.\n")
        })
      })
    })
    
    # Additional polar plot variations
    cat("Creating additional polar plot variations...\n")
    
    # Polar plot with different statistics
    tryCatch({
      polar_mean <- polarPlot(valid_data, 
                             pollutant = ufp_col,
                             statistic = "mean",
                             k = 50,
                             main = "Polar Plot: UFP Mean Concentrations")
      print(polar_mean)
    }, error = function(e) {
      cat("Error creating mean polar plot:", e$message, "\n")
    })
    
    # Polar plot with count statistic (more robust)
    tryCatch({
      polar_count <- polarPlot(valid_data, 
                              pollutant = ufp_col,
                              statistic = "nwr",
                              main = "Polar Plot: UFP Count Distribution")
      print(polar_count)
    }, error = function(e) {
      cat("Error creating count polar plot:", e$message, "\n")
    })
    
    # Polar plot with maximum statistics
    tryCatch({
      polar_max <- polarPlot(valid_data, 
                            pollutant = ufp_col,
                            statistic = "max",
                            k = 50,
                            main = "Polar Plot: UFP Maximum Concentrations")
      print(polar_max)
    }, error = function(e) {
      cat("Error creating max polar plot:", e$message, "\n")
    })
    
    # Polar plot with different color schemes
    tryCatch({
      polar_jet <- polarPlot(valid_data, 
                            pollutant = ufp_col,
                            cols = "jet",
                            k = 50,
                            main = "Polar Plot: UFP Concentrations (Jet Colors)")
      print(polar_jet)
    }, error = function(e) {
      cat("Error creating jet color polar plot:", e$message, "\n")
    })
    
  } else {
    cat("Warning: No wind direction/speed columns found.\n")
    cat("Available columns:", paste(colnames(eastie_data), collapse = ", "), "\n")
    cat("Polar plots require wind direction and wind speed data.\n")
  }
  
} else {
  cat("Error: UFP particle concentration columns not found in the data.\n")
  cat("Available columns:", paste(colnames(eastie_data), collapse = ", "), "\n")
}

# Summary statistics for UFP concentrations if they exist
if(length(available_ufp_cols) > 0) {
  ufp_col <- available_ufp_cols[1]
  cat("\nUFP Concentration Summary Statistics:\n")
  summary(eastie_data[[ufp_col]])
  
  # Check for missing values
  ufp_na <- sum(is.na(eastie_data[[ufp_col]]))
  ufp_total <- nrow(eastie_data)
  cat("\nUFP missing values:", ufp_na, "out of", ufp_total, "total observations\n")
  
  # Check for extreme values
  ufp_values <- eastie_data[[ufp_col]]
  ufp_values <- ufp_values[!is.na(ufp_values)]
  cat("UFP concentration range:", min(ufp_values), "to", max(ufp_values), "\n")
  cat("UFP concentration median:", median(ufp_values), "\n")
}

cat("\nScript completed!\n")
