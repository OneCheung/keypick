#!/bin/bash
set -e

# Force headless mode for MediaCrawler in production/container environment
# This modifies the MediaCrawler config to use headless mode
echo "Configuring MediaCrawler for headless mode..."

# Create a Python script to modify the config
cat > /tmp/modify_config.py << 'EOF'
import os
import fileinput
import sys

# Path to MediaCrawler config
config_path = "/app/MediaCrawler/config/base_config.py"

# Read the file
with open(config_path, 'r') as file:
    lines = file.readlines()

# Modify the config
modified = False
with open(config_path, 'w') as file:
    for line in lines:
        # Force headless mode
        if line.strip().startswith('HEADLESS ='):
            file.write('HEADLESS = True  # Modified by entrypoint.sh for container environment\n')
            modified = True
        elif line.strip().startswith('CDP_HEADLESS ='):
            file.write('CDP_HEADLESS = True  # Modified by entrypoint.sh for container environment\n')
            modified = True
        elif line.strip().startswith('ENABLE_CDP_MODE ='):
            file.write('ENABLE_CDP_MODE = False  # Modified by entrypoint.sh for container environment\n')
            modified = True
        else:
            file.write(line)

if modified:
    print("MediaCrawler config modified for headless mode")
else:
    print("MediaCrawler config already configured")
EOF

# Run the config modification script
python /tmp/modify_config.py

# Apply memory optimization patches to MediaCrawler
if [ -f /app/patches/optimize_chromium_memory.py ]; then
    echo "Applying Chromium memory optimization patches..."
    python /app/patches/optimize_chromium_memory.py
fi

# Start the application with xvfb-run for X11 support
# The -a flag automatically selects a free server number
# The -s flag sets the screen configuration
echo "Starting application with xvfb-run..."
exec xvfb-run -a -s "-screen 0 1920x1080x24" uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}