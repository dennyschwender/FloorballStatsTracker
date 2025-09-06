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
CMD ["/bin/sh", "-c", "touch /app/gamesFiles/games.json && gunicorn -b 0.0.0.0:5000 app:app"]