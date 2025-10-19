# Eastie UFP Data Explorer

This repository contains tools for exploring and visualizing the `Eastie_UFP.rds` dataset using R and R Shiny.

## Files

- `Eastie_UFP.rds` - The main dataset (R Data Serialization format)
- `setup.R` - Installation script for required R packages
- `explore_data.R` - Basic data exploration and visualization script
- `shiny_app.R` - Interactive Shiny web application for data exploration

## Setup Instructions

### Prerequisites

- R (version 4.0 or higher recommended)
- RStudio (optional but recommended)

### Quick Start

1. **Install R packages** (run this first):
   ```r
   source("setup.R")
   ```
   This will install required packages (`shiny`, `ggplot2`, `DT`) using 12 CPU cores for faster installation.

2. **Explore the data** (choose one option):

   **Option A: Basic exploration in R console**
   ```r
   source("explore_data.R")
   ```

   **Option B: Interactive Shiny app**
   ```r
   source("shiny_app.R")
   ```

   **Option C: Manual exploration**
   ```r
   data <- readRDS("Eastie_UFP.rds")
   str(data)           # See data structure
   head(data)          # See first few rows
   summary(data)       # See summary statistics
   ```

### What You'll Get

- **Data overview**: Dimensions, column names, data types, missing values
- **Summary statistics**: For all variables in the dataset
- **Automatic visualizations**: Histograms for numeric variables, bar charts for categorical variables
- **Interactive exploration**: (Shiny app) Browse data tables, create custom plots, filter data

### Troubleshooting

- **Package installation fails**: Try running `install.packages(c("shiny", "ggplot2", "DT"))` manually
- **Shiny app won't start**: Make sure all packages are installed and try restarting R
- **Performance issues**: The setup script uses 12 cores by default; adjust `n_cores` in `setup.R` if needed

### System Requirements

- **Memory**: At least 4GB RAM recommended
- **CPU**: Multi-core processor recommended (setup uses 12 cores)
- **Storage**: ~500MB for R packages and dependencies
