FROM python:3.12-slim

# Set metadata
LABEL maintainer="Harness Custom Plugin"
LABEL description="Enhanced Harness Custom Drone Plugin with Git-based Default Values"
LABEL version="2.0.0"

# Install git and ca-certificates
RUN apt-get update && apt-get install -y git ca-certificates

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py enhanced_main.py ./
COPY src/ ./src/

# Set environment variables for better Python behavior
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Git repositories will be cloned in current working directory (/app)

# Use enhanced plugin by default, with fallback to original
ENTRYPOINT ["python", "enhanced_main.py"]