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
