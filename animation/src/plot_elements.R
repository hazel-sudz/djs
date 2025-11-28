# =============================================================================
# Plot Elements Functions
# =============================================================================
# Functions for adding visual elements (pollution circles, wind arrows) to maps.

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

# Add wind arrow to a ggplot map
# @param plot Base ggplot object
# @param wind_data Wind summary data for current time point
# @param lon_center Center longitude for arrow placement
# @param lat_center Center latitude for arrow placement
# @param map_extent List with lat_min, lat_max, lon_min, lon_max
# @return ggplot object with wind arrow added
add_wind_arrow <- function(plot, wind_data, lon_center, lat_center, map_extent) {
  # Calculate arrow scale based on map size (15% of smaller dimension)
  map_lat_range <- map_extent$lat_max - map_extent$lat_min
  map_lon_range <- map_extent$lon_max - map_extent$lon_min
  arrow_scale <- min(map_lat_range, map_lon_range) * 0.15

  # Check if we have valid wind data
  if (nrow(wind_data) == 0 || is.na(wind_data$avg_wind_u) || is.na(wind_data$avg_wind_v)) {
    # No wind data - just show center point
    return(plot +
      geom_point(
        data = data.frame(x = lon_center, y = lat_center),
        aes(x = x, y = y),
        color = "darkblue",
        size = 3,
        shape = 21,
        fill = "white",
        stroke = 2
      ))
  }

  # Calculate arrow endpoint
  arrow_end <- calculate_wind_arrow(
    lon_center, lat_center,
    wind_data$avg_wind_u[1],
    wind_data$avg_wind_v[1],
    wind_data$avg_wind_speed[1],
    arrow_scale
  )

  if (is.null(arrow_end)) {
    # Invalid wind - just show center point
    return(plot +
      geom_point(
        data = data.frame(x = lon_center, y = lat_center),
        aes(x = x, y = y),
        color = "darkblue",
        size = 3,
        shape = 21,
        fill = "white",
        stroke = 2
      ))
  }

  # Create arrow data frame
  arrow_df <- data.frame(
    x = lon_center,
    y = lat_center,
    xend = arrow_end$end_lon,
    yend = arrow_end$end_lat
  )

  # Add wind arrow and center point to plot
  plot +
    geom_segment(
      data = arrow_df,
      aes(x = x, y = y, xend = xend, yend = yend),
      arrow = arrow(length = unit(0.3, "cm"), type = "closed"),
      color = "darkblue",
      linewidth = 2,
      alpha = 0.8
    ) +
    geom_point(
      data = data.frame(x = lon_center, y = lat_center),
      aes(x = x, y = y),
      color = "darkblue",
      size = 3,
      shape = 21,
      fill = "white",
      stroke = 2
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
