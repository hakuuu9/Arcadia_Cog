# Use official Python runtime as a parent image
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements.txt first to leverage Docker cache if requirements don't change
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code into the container
COPY . .

# Ensure start.sh has Unix line endings and bash compatible
RUN chmod +x start.sh

# Expose port if needed (usually for web apps, can omit for Discord bots)
# EXPOSE 8080

# Run start.sh via bash
CMD ["bash", "start.sh"]
