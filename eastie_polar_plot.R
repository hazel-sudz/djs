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
    
    # Daily polar plots - aggregate by day
    cat("Creating daily polar plots...\n")
    
    # Add date column for daily aggregation
    valid_data$date <- as.Date(valid_data$timestamp_local.x)
    unique_dates <- unique(valid_data$date)
    cat("Number of unique days:", length(unique_dates), "\n")
    cat("Date range:", min(unique_dates), "to", max(unique_dates), "\n")
    
    # Remove extreme outliers for better visualization
    ufp_values <- valid_data[[ufp_col]]
    ufp_quantiles <- quantile(ufp_values, probs = c(0.01, 0.99), na.rm = TRUE)
    cat("UFP concentration 1st and 99th percentiles:", ufp_quantiles, "\n")
    
    # Filter out extreme outliers (keep 1st to 99th percentile)
    valid_data_clean <- valid_data[ufp_values >= ufp_quantiles[1] & ufp_values <= ufp_quantiles[2], ]
    cat("Observations after outlier removal:", nrow(valid_data_clean), "out of", nrow(valid_data), "\n")
    
    # Debug: Check how many observations remain for each day after outlier removal
    cat("\nDaily observation counts after outlier removal:\n")
    for(i in 1:length(unique_dates)) {
      current_date <- unique_dates[i]
      day_data_original <- valid_data[valid_data$date == current_date, ]
      day_count_clean <- sum(valid_data_clean$date == current_date, na.rm = TRUE)
      day_ufp_range <- range(day_data_original[[ufp_col]], na.rm = TRUE)
      cat(as.character(current_date), ":", day_count_clean, "observations (original:", nrow(day_data_original), 
          ", UFP range:", round(day_ufp_range[1]), "-", round(day_ufp_range[2]), ")\n")
    }
    
    # Debug: Check the data structure for daily plots
    cat("\nDebug information for daily plots:\n")
    cat("Wind direction column:", wd_col, "\n")
    cat("Wind speed column:", ws_col, "\n")
    cat("UFP concentration column:", ufp_col, "\n")
    
    # Check a sample of the data
    sample_data <- valid_data[1:5, c(wd_col, ws_col, ufp_col)]
    cat("Sample data (first 5 rows):\n")
    print(sample_data)
    
    # Create polar plot for each day using cleaned data
    for(i in 1:length(unique_dates)) {
      current_date <- unique_dates[i]
      day_data <- valid_data_clean[valid_data_clean$date == current_date, ]
      
      cat("\nProcessing", as.character(current_date), "-", nrow(day_data), "observations\n")
      
      if(nrow(day_data) >= 50) {  # Need sufficient data for meaningful polar plot
        # Check for wind direction variation (avoid constant wind direction)
        wd_range <- range(day_data[[wd_col]], na.rm = TRUE)
        wd_variation <- wd_range[2] - wd_range[1]
        
        cat("Wind direction range:", wd_range, "(variation:", wd_variation, "degrees)\n")
        cat("Wind speed range:", range(day_data[[ws_col]], na.rm = TRUE), "\n")
        cat("UFP concentration range:", range(day_data[[ufp_col]], na.rm = TRUE), "\n")
        
        # Skip days with insufficient wind direction variation
        if(wd_variation < 30) {
          cat("Skipping", as.character(current_date), "- insufficient wind direction variation (", wd_variation, "degrees)\n")
          next
        }
        
        # Check for valid wind data in this day
        valid_wd_day <- !is.na(day_data[[wd_col]]) & day_data[[wd_col]] >= 0 & day_data[[wd_col]] <= 360
        valid_ws_day <- !is.na(day_data[[ws_col]]) & day_data[[ws_col]] >= 0
        valid_ufp_day <- !is.na(day_data[[ufp_col]]) & day_data[[ufp_col]] > 0
        
        cat("Valid wind direction:", sum(valid_wd_day), "\n")
        cat("Valid wind speed:", sum(valid_ws_day), "\n")
        cat("Valid UFP:", sum(valid_ufp_day), "\n")
        
        # Create clean day data
        clean_day_data <- day_data[valid_wd_day & valid_ws_day & valid_ufp_day, ]
        cat("Clean observations for this day:", nrow(clean_day_data), "\n")
        
        if(nrow(clean_day_data) >= 50) {
          # Use consistent format for all days (scatter plot + polar frequency plot)
          unique_wd <- length(unique(clean_day_data[[wd_col]]))
          cat("Unique wind directions:", unique_wd, "\n")
          cat("Creating consistent plots for", as.character(current_date), "...\n")
          
          # Create scatter plot for all days
          tryCatch({
            scatter_plot <- scatterPlot(clean_day_data, 
                                       x = wd_col, 
                                       y = ufp_col,
                                       z = ws_col,
                                       main = paste("Daily Scatter Plot:", as.character(current_date), "- Wind Direction vs UFP"),
                                       xlab = "Wind Direction (degrees)",
                                       ylab = "UFP Concentration")
            print(scatter_plot)
          }, error = function(e) {
            cat("Error creating scatter plot:", e$message, "\n")
          })
          
          # Create polar frequency plot for all days
          tryCatch({
            freq_plot <- polarFreq(clean_day_data, 
                                  pollutant = ufp_col,
                                  main = paste("Daily Polar Frequency:", as.character(current_date), "- UFP by Wind Direction"))
            print(freq_plot)
          }, error = function(e) {
            cat("Error creating polar frequency plot:", e$message, "\n")
          })
          
        } else {
          cat("Skipping", as.character(current_date), "- insufficient clean data (", nrow(clean_day_data), "observations)\n")
        }
      } else {
        cat("Skipping", as.character(current_date), "- insufficient data (", nrow(day_data), "observations)\n")
      }
    }
    
    # Create a summary polar plot showing all days combined with day as type
    cat("Creating summary polar plot by day...\n")
    tryCatch({
      summary_polar <- polarPlot(valid_data_clean, 
                                pollutant = ufp_col,
                                type = "date",
                                k = 50,
                                main = "Summary Polar Plot: UFP Concentrations by Day")
      print(summary_polar)
    }, error = function(e) {
      cat("Error creating summary polar plot by day:", e$message, "\n")
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
