FROM python:3.11.6-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs

# Set permissions
RUN chmod +x install.sh setup_sample_rules.py

# Expose any ports if needed (for future web interface)
# EXPOSE 8080

# Default command
CMD ["python3", "src.main"]
