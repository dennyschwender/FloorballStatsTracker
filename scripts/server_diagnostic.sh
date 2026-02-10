#!/bin/bash
# FloorballStatsTracker Server Diagnostic Script
# Run this on your Linux server to check configuration

echo "=== 1. Checking .env file ==="
if [ -f .env ]; then
    echo "✓ .env file exists"
    echo "Environment variables (non-empty lines):"
    grep -v '^#' .env | grep -v '^$'
else
    echo "✗ .env file MISSING!"
fi

echo ""
echo "=== 2. Checking Required Directories ==="
for dir in gamesFiles rosters templates static tests routes services utils models; do
    if [ -d "$dir" ]; then
        echo "✓ $dir exists (permissions: $(stat -c '%a' $dir 2>/dev/null || stat -f '%A' $dir))"
    else
        echo "✗ $dir MISSING"
    fi
done

echo ""
echo "=== 3. Checking Required Files ==="
for file in app.py config.py requirements.txt gamesFiles/games.json; do
    if [ -f "$file" ]; then
        echo "✓ $file exists (permissions: $(stat -c '%a' $file 2>/dev/null || stat -f '%A' $file))"
    else
        echo "✗ $file MISSING"
    fi
done

echo ""
echo "=== 4. Checking Python and Pip ==="
which python3
python3 --version
which pip3
pip3 --version

echo ""
echo "=== 5. Checking Python Dependencies ==="
pip3 list | grep -E "Flask|python-dotenv|gunicorn|Flask-WTF"

echo ""
echo "=== 6. Testing Configuration Import ==="
python3 -c "from config import REQUIRED_PIN, SECRET_KEY, GAMES_FILE; print('✓ Config loads successfully'); print(f'PIN length: {len(REQUIRED_PIN)} chars'); print(f'SECRET_KEY length: {len(SECRET_KEY)} chars')" 2>&1

echo ""
echo "=== 7. Testing App Import ==="
python3 -c "from app import app; print('✓ App imports successfully'); print(f'Blueprints: {len(app.blueprints)}')" 2>&1

echo ""
echo "=== 8. Checking Process Status ==="
ps aux | grep -E "gunicorn|flask|python.*app.py" | grep -v grep

echo ""
echo "=== 9. Checking Systemd Service (if exists) ==="
if systemctl list-unit-files | grep -q floorball; then
    systemctl status floorball* --no-pager
else
    echo "No systemd service found"
fi

echo ""
echo "=== 10. Checking Recent Logs ==="
if [ -d "logs" ]; then
    echo "Application logs:"
    ls -lh logs/
    echo ""
    echo "Last 20 lines of latest log:"
    tail -20 logs/*.log 2>/dev/null | head -20
fi

echo ""
echo "=== 11. Testing Port Availability ==="
netstat -tlnp 2>/dev/null | grep -E ":5000|:8000" || ss -tlnp | grep -E ":5000|:8000"

echo ""
echo "=== DIAGNOSTIC COMPLETE ==="
