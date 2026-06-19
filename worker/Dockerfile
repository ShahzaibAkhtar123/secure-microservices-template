# Use lightweight Python 3.11 Alpine (smaller, more secure)
FROM python:3.11-alpine

# Set working directory inside container
WORKDIR /app

# Install system dependencies needed for PostgreSQL and Redis
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev \
    curl

# Copy requirements first (for Docker caching - speeds up rebuilds)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

# Create directory for logs
RUN mkdir -p /var/log/app

# Expose port 8080 (so Docker knows this port is used)
EXPOSE 8080

# Start the application
CMD ["python", "-u", "app.py"]
