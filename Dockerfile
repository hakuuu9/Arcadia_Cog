# Use official Python slim image with version 3.12
FROM python:3.12-slim

# Avoid prompts during package installs
ENV DEBIAN_FRONTEND=noninteractive

# Install ffmpeg and system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg git curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy all files to container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make sure start.sh is executable
RUN chmod +x start.sh

# Run the bot using start.sh
CMD ["bash", "start.sh"]
