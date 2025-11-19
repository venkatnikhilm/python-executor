# Dockerfile
# Production-ready Python script executor with nsjail sandboxing

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and nsjail
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libnl-route-3-dev \
    libnl-3-dev \
    libprotobuf-dev \
    protobuf-compiler \
    bison \
    flex \
    git \
    && rm -rf /var/lib/apt/lists/*

# Build and install nsjail from source
RUN git clone --depth 1 https://github.com/google/nsjail.git /tmp/nsjail && \
    cd /tmp/nsjail && \
    make && \
    cp /tmp/nsjail/nsjail /usr/bin/nsjail && \
    chmod +x /usr/bin/nsjail && \
    cd / && \
    rm -rf /tmp/nsjail

# Create necessary directories
RUN mkdir -p /app/config /app/app

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ /app/app/
COPY config/ /app/config/

# Ensure proper permissions for temp directory
RUN mkdir -p /tmp && chmod 1777 /tmp

# Create logs directory
RUN mkdir -p /var/log && chmod 755 /var/log

# Expose port 8080
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV FLASK_APP=app.main:app

# Run as root (required for nsjail to function properly)
# nsjail creates namespaces which require root privileges
USER root

# Run the application using gunicorn
# --workers 2: Use 2 worker processes for handling requests
# --timeout 30: 30 second timeout per request
# --bind 0.0.0.0:8080: Listen on all interfaces on port 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "30", "--access-logfile", "-", "--error-logfile", "-", "app.main:app"]