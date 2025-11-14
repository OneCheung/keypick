# KeyPick Makefile
# Project management commands

.PHONY: help setup clean dev test deploy docker-build docker-run

help: ## Show this help message
	@echo "KeyPick - Social Media Crawler Platform"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

setup: ## Initial project setup
	@echo "Setting up KeyPick..."
	@python setup.py

clean: ## Clean project files (remove cache, logs, temp files)
	@echo "Cleaning project..."
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*~" -delete
	@find . -type f -name ".DS_Store" -delete
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build/ dist/ *.egg-info
	@rm -rf MediaCrawler/data/
	@rm -rf MediaCrawler/browser_data/
	@rm -rf logs/
	@echo "Clean complete!"

dev: ## Run development server
	@echo "Starting development server..."
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	@echo "Running tests..."
	pytest tests/ -v

lint: ## Run code linting
	@echo "Running linters..."
	ruff check .
	black --check .

format: ## Format code
	@echo "Formatting code..."
	black .
	ruff check --fix .

docker-build: ## Build Docker image
	@echo "Building Docker image..."
	docker build -t keypick .

docker-run: ## Run Docker container locally
	@echo "Running Docker container..."
	@if [ -f .env ]; then \
		docker run --rm -it --env-file .env -p 8080:8080 --name keypick keypick; \
	else \
		docker run --rm -it -e PORT=8080 -e LOG_LEVEL=DEBUG -p 8080:8080 --name keypick keypick; \
	fi

deploy: ## Deploy to Fly.io
	@echo "Deploying to Fly.io..."
	@if ! command -v fly &> /dev/null; then \
		echo "Error: Fly CLI not installed. Install it with: curl -L https://fly.io/install.sh | sh"; \
		exit 1; \
	fi
	fly deploy
	@echo ""
	@echo "Deployment complete! Your app: https://keypick.fly.dev"
	@echo "View logs: fly logs"
	@echo "Check status: fly status"

deploy-scale: ## Scale Fly.io memory if needed
	@echo "Scaling Fly.io memory to 2GB..."
	fly scale memory 2048

ssh: ## SSH into Fly.io container
	fly ssh console

logs: ## View Fly.io logs
	fly logs --tail

status: ## Check Fly.io deployment status
	fly status

api-docs: ## Generate API documentation
	@echo "API documentation available at http://localhost:8000/docs when server is running"

submodule-update: ## Update MediaCrawler submodule
	@echo "Updating MediaCrawler submodule..."
	git submodule update --init --recursive
	git submodule foreach git pull origin main