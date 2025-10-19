# Setup script for exploring Eastie_UFP.rds
# Run this script first to install required packages

cat("Setting up multithreading with 12 cores...\n")

# Set number of cores for parallel processing
n_cores <- 12
options(Ncpus = n_cores)

# Configure parallel processing
if (require(parallel, quietly = TRUE)) {
  cat("Parallel processing available\n")
} else {
  cat("Installing parallel package...\n")
  install.packages("parallel", Ncpus = n_cores)
  library(parallel)
}

cat(paste("Installing required R packages with", n_cores, "cores...\n"))

# Install packages if they don't exist
required_packages <- c("shiny", "ggplot2", "DT")

# Check which packages need installation
packages_to_install <- c()
for (pkg in required_packages) {
  if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
    packages_to_install <- c(packages_to_install, pkg)
    cat(paste(pkg, "needs to be installed\n"))
  } else {
    cat(paste(pkg, "is already installed\n"))
  }
}

# Install all missing packages in parallel
if (length(packages_to_install) > 0) {
  cat(paste("Installing", length(packages_to_install), "packages in parallel...\n"))
  install.packages(packages_to_install, 
                   dependencies = TRUE, 
                   Ncpus = n_cores,
                   type = "binary")  # Use binary packages when possible for faster installation
}

cat("\nSetup complete! You can now:\n")
cat("1. Run 'source('explore_data.R')' to explore the data in the console\n")
cat("2. Run 'source('shiny_app.R')' to launch an interactive Shiny app\n")
cat("3. Or run 'R' and then load the data with: data <- readRDS('Eastie_UFP.rds')\n")
