# Load the RDS file
data <- readRDS("Eastie_UFP.rds")

# Basic information about the data
cat("Data structure:\n")
str(data)

cat("\nData dimensions:\n")
print(dim(data))

cat("\nColumn names:\n")
print(colnames(data))

cat("\nFirst few rows:\n")
print(head(data))

cat("\nData summary:\n")
print(summary(data))

# If it's a dataframe, show more details
if (is.data.frame(data)) {
  cat("\nData types:\n")
  print(sapply(data, class))
  
  cat("\nMissing values per column:\n")
  print(colSums(is.na(data)))
}

# Basic visualization (if ggplot2 is available)
if (require(ggplot2, quietly = TRUE)) {
  cat("\nCreating basic visualizations...\n")
  
  # For numeric columns, create histograms
  numeric_cols <- sapply(data, is.numeric)
  if (sum(numeric_cols) > 0) {
    numeric_data <- data[, numeric_cols, drop = FALSE]
    
    # Create histograms for first few numeric columns
    for (i in 1:min(4, ncol(numeric_data))) {
      col_name <- colnames(numeric_data)[i]
      p <- ggplot(data, aes_string(x = col_name)) +
        geom_histogram(bins = 30, fill = "skyblue", alpha = 0.7) +
        labs(title = paste("Distribution of", col_name),
             x = col_name, y = "Frequency")
      print(p)
    }
  }
  
  # For categorical columns, create bar plots
  categorical_cols <- sapply(data, function(x) is.factor(x) || is.character(x))
  if (sum(categorical_cols) > 0) {
    cat_cols <- data[, categorical_cols, drop = FALSE]
    
    # Create bar plots for first few categorical columns
    for (i in 1:min(3, ncol(cat_cols))) {
      col_name <- colnames(cat_cols)[i]
      p <- ggplot(data, aes_string(x = col_name)) +
        geom_bar(fill = "lightcoral", alpha = 0.7) +
        labs(title = paste("Distribution of", col_name),
             x = col_name, y = "Count") +
        theme(axis.text.x = element_text(angle = 45, hjust = 1))
      print(p)
    }
  }
} else {
  cat("\nTo create visualizations, install ggplot2: install.packages('ggplot2')\n")
}
