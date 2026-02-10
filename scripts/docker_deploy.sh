#!/bin/bash
# Docker Deployment Script for FloorballStatsTracker
# Run this on your Docker server after pulling the latest code

set -e

echo "=== FloorballStatsTracker Docker Deployment ==="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo ""
    echo "Please create .env file with:"
    echo "  FLOORBALL_PIN=your_secure_pin"
    echo "  FLASK_SECRET_KEY=your_secret_key"
    echo "  SESSION_COOKIE_SECURE=True"
    echo "  DEFAULT_LANG=en"
    echo ""
    echo "You can copy .env.docker as a template:"
    echo "  cp .env.docker .env"
    echo "  nano .env  # Edit with your values"
    exit 1
fi

echo "✓ .env file found"

# Create necessary directories
echo ""
echo "=== Creating directories ==="
mkdir -p gamesFiles rosters logs
chmod 755 gamesFiles rosters logs

# Initialize games.json if it doesn't exist
if [ ! -f gamesFiles/games.json ]; then
    echo '[]' > gamesFiles/games.json
    echo "✓ Created gamesFiles/games.json"
fi

# Stop and remove old containers
echo ""
echo "=== Stopping old containers ==="
docker-compose down || true

# Rebuild the image with latest code
echo ""
echo "=== Building Docker image ==="
docker-compose build --no-cache

# Start the container
echo ""
echo "=== Starting container ==="
docker-compose up -d

# Wait for container to start
echo ""
echo "=== Waiting for container to start ==="
sleep 5

# Check container status
echo ""
echo "=== Container Status ==="
docker-compose ps

# Show logs
echo ""
echo "=== Recent Logs ==="
docker-compose logs --tail=20

# Test if app is responding
echo ""
echo "=== Testing App Response ==="
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 | grep -q "200\|302"; then
    echo "✅ App is responding successfully!"
else
    echo "⚠️  App might not be responding correctly. Check logs:"
    echo "   docker-compose logs -f"
fi

echo ""
echo "=== Deployment Complete ==="
echo "Access the app at: http://your-server-ip:5000"
echo ""
echo "Useful commands:"
echo "  View logs:     docker-compose logs -f"
echo "  Restart:       docker-compose restart"
echo "  Stop:          docker-compose down"
echo "  Shell access:  docker exec -it floorball-stats-tracker /bin/bash"
