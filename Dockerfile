# Use official Python image (latest security patches)
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Install dependencies as root
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Create a non-root user and give it ownership of app files
RUN adduser --disabled-password --gecos '' appuser \
    && mkdir -p /app/gamesFiles /app/rosters /app/logs \
    && chown -R appuser:appuser /app

USER appuser

# Expose port (Flask default is 5000)
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Verify the app imports correctly then start gunicorn
CMD ["sh", "-c", \
     "python3 -c 'from app import app; print(\"✓ App imports successfully\")' && \
      gunicorn -b 0.0.0.0:5000 --workers 2 --timeout 120 \
               --log-level info --capture-output --enable-stdio-inheritance \
               app:app"]
