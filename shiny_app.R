library(shiny)
library(ggplot2)
library(DT)

# Define UI
ui <- fluidPage(
  titlePanel("Eastie UFP Data Explorer"),
  
  sidebarLayout(
    sidebarPanel(
      h3("Data Overview"),
      verbatimTextOutput("dataInfo"),
      
      h3("Visualization Options"),
      selectInput("plotType", "Plot Type:",
                  choices = c("Histogram", "Bar Plot", "Scatter Plot", "Box Plot")),
      
      conditionalPanel(
        condition = "input.plotType == 'Histogram' || input.plotType == 'Bar Plot'",
        selectInput("var1", "Select Variable:",
                    choices = NULL)
      ),
      
      conditionalPanel(
        condition = "input.plotType == 'Scatter Plot'",
        selectInput("varX", "X Variable:",
                    choices = NULL),
        selectInput("varY", "Y Variable:",
                    choices = NULL)
      ),
      
      conditionalPanel(
        condition = "input.plotType == 'Box Plot'",
        selectInput("varBox", "Variable:",
                    choices = NULL),
        selectInput("groupVar", "Group By (optional):",
                    choices = NULL)
      ),
      
      h3("Data Table"),
      p("Use the table below to browse the data:"),
      checkboxInput("showAll", "Show all rows", FALSE)
    ),
    
    mainPanel(
      plotOutput("plot", height = "500px"),
      br(),
      h3("Data Table"),
      DTOutput("dataTable")
    )
  )
)

# Define server logic
server <- function(input, output) {
  
  output$dataInfo <- renderText({
    paste(
      "Dimensions:", paste(dim(data), collapse = " x "), "\n",
      "Columns:", ncol(data), "\n",
      "Rows:", nrow(data), "\n",
      "Numeric columns:", sum(sapply(data, is.numeric)), "\n",
      "Character/Factor columns:", sum(sapply(data, function(x) is.factor(x) || is.character(x)))
    )
  })
  
  output$plot <- renderPlot({
    tryCatch({
      if (input$plotType == "Histogram") {
        if (is.numeric(data[[input$var1]])) {
          ggplot(data, aes(x = .data[[input$var1]])) +
            geom_histogram(bins = 30, fill = "skyblue", alpha = 0.7) +
            labs(title = paste("Distribution of", input$var1),
                 x = input$var1, y = "Frequency") +
            theme_minimal()
        } else {
          ggplot(data, aes(x = .data[[input$var1]])) +
            geom_bar(fill = "lightcoral", alpha = 0.7) +
            labs(title = paste("Distribution of", input$var1),
                 x = input$var1, y = "Count") +
            theme_minimal() +
            theme(axis.text.x = element_text(angle = 45, hjust = 1))
        }
      } else if (input$plotType == "Bar Plot") {
        ggplot(data, aes(x = .data[[input$var1]])) +
          geom_bar(fill = "lightcoral", alpha = 0.7) +
          labs(title = paste("Distribution of", input$var1),
               x = input$var1, y = "Count") +
          theme_minimal() +
          theme(axis.text.x = element_text(angle = 45, hjust = 1))
      } else if (input$plotType == "Scatter Plot") {
        ggplot(data, aes(x = .data[[input$varX]], y = .data[[input$varY]])) +
          geom_point(alpha = 0.6, color = "darkblue") +
          labs(title = paste("Scatter Plot:", input$varX, "vs", input$varY),
               x = input$varX, y = input$varY) +
          theme_minimal()
      } else if (input$plotType == "Box Plot") {
        if (input$groupVar == "None") {
          ggplot(data, aes(y = .data[[input$varBox]])) +
            geom_boxplot(fill = "lightgreen", alpha = 0.7) +
            labs(title = paste("Box Plot of", input$varBox),
                 y = input$varBox) +
            theme_minimal()
        } else {
          ggplot(data, aes(x = .data[[input$groupVar]], y = .data[[input$varBox]])) +
            geom_boxplot(fill = "lightgreen", alpha = 0.7) +
            labs(title = paste("Box Plot of", input$varBox, "by", input$groupVar),
                 x = input$groupVar, y = input$varBox) +
            theme_minimal() +
            theme(axis.text.x = element_text(angle = 45, hjust = 1))
        }
      }
    }, error = function(e) {
      ggplot() + 
        annotate("text", x = 0.5, y = 0.5, 
                label = paste("Error creating plot:", e$message), 
                size = 5) +
        theme_void()
    })
  })
  
  output$dataTable <- renderDT({
    if (input$showAll) {
      data
    } else {
      head(data, 100)
    }
  }, options = list(pageLength = 10, scrollX = TRUE))
}

# Run the application
cat("Starting Shiny app on port 8080...\n")
cat("The app should open automatically in your browser at: http://localhost:8080\n")
cat("If it doesn't open, manually navigate to: http://localhost:8080\n")
cat("Press Ctrl+C (or Cmd+C on Mac) to stop the app when you're done.\n\n")

shinyApp(ui = ui, server = server, 
         options = list(launch.browser = TRUE, port = 8080))
