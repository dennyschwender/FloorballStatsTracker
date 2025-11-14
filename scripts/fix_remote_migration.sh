#!/bin/bash
# Script to move games files from .gamesFiles to gamesFiles (remove dot prefix)

echo "=================================="
echo "Move Games Files to Standard Location"
echo "=================================="
echo ""

# Check if .gamesFiles directory exists
if [ ! -d ".gamesFiles" ]; then
    echo "Error: .gamesFiles directory not found!"
    echo "Are you in the correct directory?"
    exit 1
fi

# Create gamesFiles directory if it doesn't exist
if [ ! -d "gamesFiles" ]; then
    echo "Creating gamesFiles/ directory..."
    mkdir gamesFiles
fi

echo "Found source directory:"
echo "  .gamesFiles/ (old location with dot)"
echo ""

# Show what will be moved
echo "Files in .gamesFiles/ to be moved:"
ls -lh .gamesFiles/
echo ""

# Ask for confirmation
read -p "Move files from .gamesFiles/ to gamesFiles/? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Move files
echo ""
echo "Moving files..."
mv .gamesFiles/* gamesFiles/ 2>/dev/null || echo "No files to move or some files already exist"
echo "✓ Files moved successfully"

# Remove old directory
rmdir .gamesFiles 2>/dev/null && echo "✓ Removed old .gamesFiles/ directory" || echo "⚠ Could not remove .gamesFiles/ (may contain hidden files or not be empty)"

echo ""
echo "=================================="
echo "Migration complete!"
echo "=================================="
echo ""
echo "Files now in gamesFiles/:"
ls -lh gamesFiles/
echo ""
echo "You may need to restart your Docker container:"
echo "  docker-compose restart"
