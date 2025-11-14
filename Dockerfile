# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# Note: libgl1 and libglib2.0-0 are required for opencv-python
# Node.js is required for pyexecjs (used by MediaCrawler's Douyin crawler)
# xvfb is required for running browser in headless mode
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for pyexecjs)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml .
COPY README.md .

# Install Python dependencies using uv
RUN uv pip install --system -e .

# Install Playwright browsers and dependencies
# Note: Playwright requires system dependencies for browser automation
# Use python -m playwright to ensure we use the correct Python environment
RUN python -m playwright install chromium \
    && python -m playwright install-deps chromium

# Copy application code
COPY api/ ./api/
COPY MediaCrawler/ ./MediaCrawler/

# Copy patches for memory optimization
COPY patches/ ./patches/

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create logs directory
RUN mkdir -p logs

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
# Set display for xvfb
ENV DISPLAY=:99

# Expose port (Fly.io uses 8080)
EXPOSE 8080

# Use entrypoint script to configure and start the application
ENTRYPOINT ["/app/entrypoint.sh"]