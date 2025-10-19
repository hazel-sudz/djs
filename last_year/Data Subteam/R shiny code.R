library(shiny)
library(openair)
library(dplyr)
library(gridExtra)
library(grid)
library(ggplot2)

load("G:/My Drive/Air Partners/data/graphableData.RData")

# Function to assign season based on month
getSeason <- function(dates) {
  m <- as.numeric(format(dates, "%m"))
  ifelse(m %in% c(12, 1, 2), "Winter",
         ifelse(m %in% c(3, 4, 5), "Spring",
                ifelse(m %in% c(6, 7, 8), "Summer", "Fall")))
}

# Helper function to apply log transformation to a pollutant column
applyLog <- function(d, poll) {
  d %>% mutate(!!poll := ifelse(.data[[poll]] > 0, log10(.data[[poll]]), NA))
}

# Helper function for Box Plot with summary stats
makeBoxPlot <- function(data, label, poll, logScale) {
  stat_mean <- mean(data[[poll]], na.rm = TRUE)
  stat_median <- median(data[[poll]], na.rm = TRUE)
  stat_sd <- sd(data[[poll]], na.rm = TRUE)
  
  p <- ggplot(data, aes(x = "", y = .data[[poll]])) +
    geom_boxplot()
  
  if (logScale) {
    p <- p + scale_y_log10()
  }
  
  p <- p +
    labs(title = paste(label, poll, "Box Plot"), x = "") +
    theme(axis.text.x = element_blank())
  
  stats_text <- paste("Mean:", round(stat_mean, 2),
                      "Median:", round(stat_median, 2),
                      "SD:", round(stat_sd, 2))
  
  gridExtra::grid.arrange(
    p,
    grid::textGrob(stats_text, gp = grid::gpar(fontsize = 12)),
    ncol = 1, heights = c(4, 1)
  )
}

# Helper function for openair plots by season with a label
makeSeasonPlot <- function(data, sea, poll, type, title_label) {
  plot_grob <- grid::grid.grabExpr({
    if (type == "Time Series") {
      timePlot(data,
               pollutant = poll,
               y.relation = "same",
               main = title_label)
    } else if (type == "Calendar Plot") {
      calendarPlot(data,
                   pollutant = poll,
                   main = title_label)
    } else if (type == "Polar Plot") {
      polarPlot(data,
                pollutant = poll,
                main = title_label)
    } else if (type == "Diurnal Profile") {
      tv <- timeVariation(data, pollutant = poll)
      plot(tv, subset = "hour")
    }
  })
  label_grob <- grid::textGrob(sea, gp = grid::gpar(fontsize = 16, fontface = "bold"))
  gridExtra::arrangeGrob(label_grob, plot_grob, ncol = 1, heights = c(0.15, 0.85))
}

sensorChoices <- c("All Sensors",
                   "All Sensors - Side by Side",
                   unique(mod_met$sn))

ui <- fluidPage(
  titlePanel("AQ Sensor Data Analysis"),
  sidebarLayout(
    sidebarPanel(
      selectInput("sensor", "Sensor", choices = sensorChoices),
      selectInput("pollutant", "Pollutant", choices = c("pm1", "pm25", "pm10")),
      selectInput("plotType", "Graph Type",
                  choices = c("Time Series", "Calendar Plot", "Polar Plot",
                              "Diurnal Profile", "Box Plot")),
      checkboxInput("exclude1", "Exclude Date Range 1", FALSE),
      conditionalPanel(
        condition = "input.exclude1 == true",
        dateInput("start_date1", "Start Date 1"),
        dateInput("end_date1", "End Date 1")
      ),
      checkboxInput("exclude2", "Exclude Date Range 2", FALSE),
      conditionalPanel(
        condition = "input.exclude2 == true",
        dateInput("start_date2", "Start Date 2"),
        dateInput("end_date2", "End Date 2")
      ),
      checkboxInput("separateSeason", "Separate by Season", FALSE),
      checkboxInput("logScale", "Logarithmic Scale", FALSE),
      actionButton("update", "Update Graph")
    ),
    mainPanel(
      plotOutput("plotOutput")
    )
  )
)

server <- function(input, output, session) {
  sensorData <- reactive({
    d <- if (input$sensor %in% c("All Sensors", "All Sensors - Side by Side")) {
      mod_met
    } else {
      mod_met %>% filter(sn == input$sensor)
    }
    if (input$exclude1) {
      d <- d %>% filter(as.Date(date) < as.Date(input$start_date1) |
                          as.Date(date) > as.Date(input$end_date1))
    }
    if (input$exclude2) {
      d <- d %>% filter(as.Date(date) < as.Date(input$start_date2) |
                          as.Date(date) > as.Date(input$end_date2))
    }
    d
  })
  
  output$plotOutput <- renderPlot({
    req(input$update)
    isolate({
      data <- sensorData()
      poll <- input$pollutant
      type <- input$plotType
      
      # For openair plots (except Box and Diurnal), apply log transformation if needed
      transformData <- function(d) {
        if (input$logScale && type %in% c("Time Series", "Calendar Plot", "Polar Plot")) {
          d <- applyLog(d, poll)
        }
        d
      }
      
      if (input$separateSeason) {
        data$season <- getSeason(as.Date(data$date))
        seasons <- sort(unique(data$season))
        plots <- lapply(seasons, function(sea) {
          d <- data %>% filter(season == sea)
          if (type %in% c("Box Plot")) {
            makeBoxPlot(d, sea, poll, input$logScale)
          } else {
            d <- transformData(d)
            title_label <- paste(sea, poll, type)
            if (input$logScale && type %in% c("Time Series", "Calendar Plot", "Polar Plot")) {
              title_label <- paste(title_label, "(Log Scale)")
            }
            makeSeasonPlot(d, sea, poll, type, title_label)
          }
        })
        gridExtra::grid.arrange(grobs = plots, ncol = length(plots))
        
      } else if (input$sensor == "All Sensors - Side by Side") {
        sensors <- unique(data$sn)
        plots <- lapply(sensors, function(sensor) {
          d <- data %>% filter(sn == sensor)
          if (type %in% c("Box Plot")) {
            makeBoxPlot(d, sensor, poll, input$logScale)
          } else {
            d <- transformData(d)
            title_label <- paste(sensor, poll, type)
            if (input$logScale && type %in% c("Time Series", "Calendar Plot", "Polar Plot")) {
              title_label <- paste(title_label, "(Log Scale)")
            }
            grid::grid.grabExpr({
              if (type == "Time Series") {
                timePlot(d,
                         pollutant = poll,
                         y.relation = "same",
                         main = title_label)
              } else if (type == "Calendar Plot") {
                calendarPlot(d,
                             pollutant = poll,
                             main = title_label)
              } else if (type == "Polar Plot") {
                polarPlot(d,
                          pollutant = poll,
                          main = title_label)
              } else if (type == "Diurnal Profile") {
                tv <- timeVariation(d, pollutant = poll)
                plot(tv, subset = "hour")
              }
            })
          }
        })
        gridExtra::grid.arrange(grobs = plots, ncol = length(plots))
        
      } else if (input$sensor == "All Sensors") {
        if (type %in% c("Box Plot")) {
          makeBoxPlot(data, "All Sensors", poll, input$logScale)
        } else {
          data <- transformData(data)
          title_label <- paste("All Sensors", poll, type)
          if (input$logScale && type %in% c("Time Series", "Calendar Plot", "Polar Plot")) {
            title_label <- paste(title_label, "(Log Scale)")
          }
          if (type == "Time Series") {
            timePlot(data,
                     pollutant = poll,
                     main = title_label)
          } else if (type == "Calendar Plot") {
            calendarPlot(data,
                         pollutant = poll,
                         main = title_label)
          } else if (type == "Polar Plot") {
            polarPlot(data,
                      pollutant = poll,
                      main = title_label)
          } else if (type == "Diurnal Profile") {
            tv <- timeVariation(data, pollutant = poll)
            plot(tv, subset = "hour")
          }
        }
        
      } else {
        if (type %in% c("Box Plot")) {
          makeBoxPlot(data, input$sensor, poll, input$logScale)
        } else {
          data <- transformData(data)
          title_label <- paste(input$sensor, poll, type)
          if (input$logScale && type %in% c("Time Series", "Calendar Plot", "Polar Plot")) {
            title_label <- paste(title_label, "(Log Scale)")
          }
          if (type == "Time Series") {
            timePlot(data,
                     pollutant = poll,
                     main = title_label)
          } else if (type == "Calendar Plot") {
            calendarPlot(data,
                         pollutant = poll,
                         main = title_label)
          } else if (type == "Polar Plot") {
            polarPlot(data,
                      pollutant = poll,
                      main = title_label)
          } else if (type == "Diurnal Profile") {
            tv <- timeVariation(data, pollutant = poll)
            plot(tv, subset = "hour")
          }
        }
      }
    })
  })
}

shinyApp(ui = ui, server = server)
