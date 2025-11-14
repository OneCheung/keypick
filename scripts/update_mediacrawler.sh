#!/bin/bash
# Update MediaCrawler submodule from remote repository

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MEDIACRAWLER_DIR="$PROJECT_ROOT/MediaCrawler"

echo "=========================================="
echo "Updating MediaCrawler from remote repository"
echo "=========================================="

# Check if MediaCrawler directory exists
if [ ! -d "$MEDIACRAWLER_DIR" ]; then
    echo "Error: MediaCrawler directory not found at $MEDIACRAWLER_DIR"
    exit 1
fi

cd "$MEDIACRAWLER_DIR"

# Check current status
echo ""
echo "Current MediaCrawler status:"
git status --short

# Check if there are local modifications
if [ -n "$(git status --porcelain)" ]; then
    echo ""
    echo "⚠️  Warning: MediaCrawler has local modifications:"
    git status --short
    
    echo ""
    read -p "Do you want to stash local changes before updating? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stashing local changes..."
        git stash push -m "Local changes before update $(date +%Y-%m-%d_%H:%M:%S)"
        STASHED=true
    else
        echo "Keeping local changes. Update may fail if there are conflicts."
        STASHED=false
    fi
else
    STASHED=false
fi

# Fetch latest changes from remote
echo ""
echo "Fetching latest changes from remote..."
git fetch origin

# Show what will be updated
echo ""
echo "Current commit:"
git log --oneline -1

echo ""
echo "Latest commit on origin/main:"
git log --oneline -1 origin/main

# Check if update is needed
CURRENT_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$CURRENT_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo ""
    echo "✅ MediaCrawler is already up to date!"
    
    # Restore stashed changes if any
    if [ "$STASHED" = true ]; then
        echo ""
        echo "Restoring stashed changes..."
        git stash pop || echo "Note: Some stashed changes may have conflicts"
    fi
    
    exit 0
fi

# Update to latest
echo ""
echo "Updating MediaCrawler to latest version..."
git pull origin main

# Restore stashed changes if any
if [ "$STASHED" = true ]; then
    echo ""
    echo "Restoring stashed changes..."
    if git stash pop; then
        echo "✅ Stashed changes restored successfully"
    else
        echo "⚠️  Warning: There may be conflicts with stashed changes"
        echo "You can resolve conflicts manually and then run: git stash drop"
    fi
fi

# Update parent repository's submodule reference
cd "$PROJECT_ROOT"
echo ""
echo "Updating parent repository's submodule reference..."
git add MediaCrawler

echo ""
echo "=========================================="
echo "✅ MediaCrawler update completed!"
echo "=========================================="
echo ""
echo "New commit:"
cd "$MEDIACRAWLER_DIR"
git log --oneline -1
echo ""
echo "Note: Don't forget to commit the submodule update in the parent repository:"
echo "  git commit -m 'Update MediaCrawler submodule'"

