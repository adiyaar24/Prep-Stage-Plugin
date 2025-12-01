FROM python:3.12-slim

# Set metadata
LABEL maintainer="Harness Custom Plugin"
LABEL description="Harness Custom Drone Plugin for CI/CD pipeline automation"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Copy application code
COPY main.py .

# Set environment variables for better Python behavior
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Use exec form for better signal handling
ENTRYPOINT ["python", "main.py"]