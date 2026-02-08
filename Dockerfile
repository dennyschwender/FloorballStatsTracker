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

# Ensure game_list.json exists, then run the app with gunicorn for production
CMD ["/bin/sh", "-c", "mkdir -p /app/gamesFiles/ /app/rosters/ /app/logs/ && gunicorn -b 0.0.0.0:5000 --workers 2 --access-logfile /app/logs/access.log --error-logfile /app/logs/error.log --log-level info app:app"]