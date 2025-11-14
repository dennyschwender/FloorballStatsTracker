#!/bin/bash
# Script to fix games files location on remote server after migration

echo "=================================="
echo "Fix Remote Migration Files"
echo "=================================="
echo ""

# Check if .gamesFiles directory exists
if [ ! -d ".gamesFiles" ]; then
    echo "Error: .gamesFiles directory not found!"
    echo "Are you in the correct directory?"
    exit 1
fi

# Check if gamesFiles directory exists (incorrectly created)
if [ ! -d "gamesFiles" ]; then
    echo "Error: gamesFiles directory not found!"
    echo "Nothing to migrate."
    exit 1
fi

echo "Found both directories:"
echo "  .gamesFiles/ (correct location for Docker)"
echo "  gamesFiles/ (incorrect location)"
echo ""

# Show what will be moved
echo "Files in gamesFiles/ to be moved:"
ls -lh gamesFiles/
echo ""

# Ask for confirmation
read -p "Move files from gamesFiles/ to .gamesFiles/? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Move files
echo ""
echo "Moving files..."
mv gamesFiles/* .gamesFiles/
echo "✓ Files moved successfully"

# Remove empty directory
rmdir gamesFiles
echo "✓ Removed empty gamesFiles/ directory"

echo ""
echo "=================================="
echo "Migration fix complete!"
echo "=================================="
echo ""
echo "Files now in .gamesFiles/:"
ls -lh .gamesFiles/
echo ""
echo "You may need to restart your Docker container:"
echo "  docker-compose restart"
