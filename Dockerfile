# Use official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Expose port (Flask default is 5000)
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Ensure directories exist and test app before starting gunicorn
CMD ["/bin/sh", "-c", "mkdir -p /app/gamesFiles/ /app/rosters/ /app/logs/ && python3 -c 'from app import app; print(\"✓ App imports successfully\")' && gunicorn -b 0.0.0.0:5000 --workers 2 --timeout 120 --log-level debug --capture-output --enable-stdio-inheritance app:app"]