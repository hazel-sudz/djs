# =============================================================================
# Plot Elements Functions
# =============================================================================
# Functions for adding visual elements (pollution circles, wind arrows) to maps.

# Format pollution value for display with units
# @param value Numeric pollution value
# @return Formatted string with units (e.g., "45.2K p/cm³")
format_pollution_label <- function(value) {
  if (value >= 1000) {
    sprintf("%.1fK p/cm³", value / 1000)
  } else {
    sprintf("%.0f p/cm³", value)
  }
}

# Format wind speed for display with units
# @param speed Wind speed in m/s
# @return Formatted string (e.g., "3.2 m/s")
format_wind_label <- function(speed) {
  sprintf("%.1f m/s", speed)
}

# Add pollution circles to a ggplot map
# @param plot Base ggplot object
# @param time_data Data for current time point with pollution values
# @param pollution_stats List with min, max, and breaks for scaling
# @return ggplot object with pollution circles added
add_pollution_circles <- function(plot, time_data, pollution_stats) {
  plot +
    geom_point(
      data = time_data,
      aes(x = lon, y = lat,
          size = pollution,
          color = pollution),
      alpha = 0.7
    ) +
    scale_size_continuous(
      name = "UFP Concentration\n(particles/cm³)",
      range = c(2, 15),
      breaks = pollution_stats$breaks,
      limits = c(pollution_stats$min, pollution_stats$max),
      guide = guide_legend(override.aes = list(alpha = 0.7, color = "gray50"))
    ) +
    scale_color_viridis_c(
      name = "UFP Concentration\n(particles/cm³)",
      option = "plasma",
      breaks = pollution_stats$breaks,
      limits = c(pollution_stats$min, pollution_stats$max),
      guide = guide_colorbar(barwidth = 1, barheight = 10)
    )
}

# Add text labels above pollution circles showing concentration values
# @param plot ggplot object with pollution circles
# @param time_data Data for current time point with pollution values
# @param label_offset Vertical offset for labels (in degrees latitude)
# @return ggplot object with pollution labels added
add_pollution_labels <- function(plot, time_data, label_offset = 0.002) {
  # Create label data with formatted values and offset positions
  label_data <- time_data %>%
    mutate(
      label = sapply(pollution, format_pollution_label),
      label_y = lat + label_offset
    )

  plot +
    geom_label(
      data = label_data,
      aes(x = lon, y = label_y, label = label),
      size = 3,
      fontface = "bold",
      fill = "white",
      alpha = 0.9,
      label.padding = unit(0.15, "lines"),
      label.size = 0.25
    )
}

# Calculate wind arrow endpoint from wind components
# @param lon_center Center longitude for arrow start
# @param lat_center Center latitude for arrow start
# @param wind_u Eastward wind component
# @param wind_v Northward wind component
# @param wind_speed Wind speed for scaling
# @param arrow_scale Base scale for arrow length
# @param max_wind_speed Maximum expected wind speed for normalization
# @return List with end coordinates (end_lon, end_lat) or NULL if invalid
calculate_wind_arrow <- function(lon_center, lat_center, wind_u, wind_v,
                                  wind_speed, arrow_scale, max_wind_speed = 6.0) {
  if (is.na(wind_speed) || wind_speed <= 0) {
    return(NULL)
  }

  # Calculate wind vector magnitude from components
  wind_magnitude <- sqrt(wind_u^2 + wind_v^2)

  if (wind_magnitude <= 0) {
    return(NULL)
  }

  # Scale arrow length based on wind speed (cap at max arrow length)
  arrow_length <- arrow_scale * min(wind_speed / max_wind_speed, 1.0)

  # Calculate end point (u is positive eastward, v is positive northward)
  list(
    end_lon = lon_center + (wind_u / wind_magnitude) * arrow_length,
    end_lat = lat_center + (wind_v / wind_magnitude) * arrow_length
  )
}

# Add wind arrow to a ggplot map with speed label
# @param plot Base ggplot object
# @param wind_data Wind summary data for current time point
# @param lon_center Center longitude for arrow placement
# @param lat_center Center latitude for arrow placement
# @param map_extent List with lat_min, lat_max, lon_min, lon_max
# @return ggplot object with wind arrow and label added
add_wind_arrow <- function(plot, wind_data, lon_center, lat_center, map_extent) {
  # Calculate arrow scale based on map size (40% of smaller dimension for bigger arrow)
  map_lat_range <- map_extent$lat_max - map_extent$lat_min
  map_lon_range <- map_extent$lon_max - map_extent$lon_min
  arrow_scale <- min(map_lat_range, map_lon_range) * 0.4

  # Check if we have valid wind data
  if (nrow(wind_data) == 0 || is.na(wind_data$avg_wind_u) || is.na(wind_data$avg_wind_v)) {
    # No wind data - just show center point
    return(plot +
      geom_point(
        data = data.frame(x = lon_center, y = lat_center),
        aes(x = x, y = y),
        color = "darkblue",
        size = 4,
        shape = 21,
        fill = "white",
        stroke = 2
      ))
  }

  wind_speed <- wind_data$avg_wind_speed[1]

  # Calculate arrow endpoint
  arrow_end <- calculate_wind_arrow(
    lon_center, lat_center,
    wind_data$avg_wind_u[1],
    wind_data$avg_wind_v[1],
    wind_speed,
    arrow_scale
  )

  if (is.null(arrow_end)) {
    # Invalid wind - just show center point with label
    return(plot +
      geom_point(
        data = data.frame(x = lon_center, y = lat_center),
        aes(x = x, y = y),
        color = "darkblue",
        size = 4,
        shape = 21,
        fill = "white",
        stroke = 2
      ) +
      geom_label(
        data = data.frame(x = lon_center, y = lat_center + 0.003),
        aes(x = x, y = y, label = "0.0 m/s"),
        size = 3.5,
        fontface = "bold",
        fill = "lightblue",
        alpha = 0.9,
        label.padding = unit(0.2, "lines")
      ))
  }

  # Create arrow data frame
  arrow_df <- data.frame(
    x = lon_center,
    y = lat_center,
    xend = arrow_end$end_lon,
    yend = arrow_end$end_lat
  )

  # Calculate label position (above the arrow endpoint)
  label_y <- max(lat_center, arrow_end$end_lat) + 0.003

  # Create wind label
  wind_label <- format_wind_label(wind_speed)

  # Add wind arrow, center point, and speed label to plot
  plot +
    geom_segment(
      data = arrow_df,
      aes(x = x, y = y, xend = xend, yend = yend),
      arrow = arrow(length = unit(0.4, "cm"), type = "closed"),
      color = "darkblue",
      linewidth = 2.5,
      alpha = 0.9
    ) +
    geom_point(
      data = data.frame(x = lon_center, y = lat_center),
      aes(x = x, y = y),
      color = "darkblue",
      size = 4,
      shape = 21,
      fill = "white",
      stroke = 2
    ) +
    geom_label(
      data = data.frame(x = lon_center, y = label_y, label = wind_label),
      aes(x = x, y = y, label = label),
      size = 3.5,
      fontface = "bold",
      fill = "lightblue",
      alpha = 0.9,
      label.padding = unit(0.2, "lines"),
      label.size = 0.3
    )
}

# Add title and labels for a specific time frame
# @param plot ggplot object
# @param current_time POSIXct timestamp for the frame
# @param title_date Date string for title (e.g., "August 1, 2025")
# @return ggplot object with titles and styled legend
add_frame_labels <- function(plot, current_time, title_date = "August 1, 2025") {
  plot +
    labs(
      title = paste("Ultrafine Particle Concentration -", title_date),
      subtitle = paste("Time:", format(current_time, "%H:%M:%S")),
      x = "Longitude",
      y = "Latitude"
    ) +
    theme(
      plot.title = element_text(size = 14, face = "bold", hjust = 0.5),
      plot.subtitle = element_text(size = 12, hjust = 0.5),
      legend.position = "right",
      legend.box = "vertical",
      legend.title = element_text(size = 10, face = "bold"),
      legend.text = element_text(size = 9)
    )
}
