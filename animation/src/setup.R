import_packages <- function(packages) {
    # Install any packages that are missing
    installed <- installed.packages()[, "Package"]
    for (p in packages) {
    if (!(p %in% installed)) {
        install.packages(p, repos = "https://cloud.r-project.org")
    }
    }

    # Load all packages
    lapply(packages, library, character.only = TRUE)
}

# Required packages
packages <- c(
  "ggspatial",
  "ggplot2",
  "gganimate",
  "dplyr",
  "lubridate",
  "viridis",
  "scales",
  "ggnewscale",
  "httr",
  "jsonlite",
  "av"
)

import_packages(packages=packages)

