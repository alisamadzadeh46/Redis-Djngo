FROM python:latest
LABEL authors="Ali samadzadeh"

# Set working directory
WORKDIR /app

# Copy project files
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt